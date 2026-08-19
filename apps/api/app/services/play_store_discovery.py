from __future__ import annotations

import html as html_lib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.repositories import AppRegistryRepository
from app.schemas.apps import PlayAppImportItem
from app.services.app_discovery import build_cbk_discovery_seeds
from app.services.relationship_backfill import sync_app_ownership_relationships

_PLAY_ORIGIN = "https://play.google.com"
_SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
_MAX_HTML_BYTES = 2 * 1024 * 1024
_MAX_JSON_BYTES = 2 * 1024 * 1024
_MAX_SERPAPI_PRODUCT_ENRICHMENTS_PER_RUN = 5
_PACKAGE_RE = re.compile(r"/store/apps/details\?[^\"'<>]*?id=([A-Za-z0-9_.]+)")
_LD_JSON_RE = re.compile(
    r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)
_LINK_RE = re.compile(
    r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)


class PlayDiscoveryUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class PlayDiscoveryResult:
    provider: str
    providers_considered: int
    search_requests: int
    detail_requests: int
    apps_ingested: int
    ownership_candidates: int
    relationship_edges: int
    failures: tuple[str, ...] = field(default_factory=tuple)


def selected_discovery_provider(requested: str, *, serpapi_api_key: str | None) -> str:
    normalized = (requested or "auto").strip().lower()
    if normalized == "auto":
        return "serpapi" if serpapi_api_key else "public_html"
    if normalized == "serpapi":
        if not serpapi_api_key:
            raise PlayDiscoveryUnavailable(
                "SerpApi is selected but KDR_SERPAPI_API_KEY is not configured"
            )
        return "serpapi"
    if normalized in {"public_html", "google_play_public_html"}:
        return "public_html"
    raise PlayDiscoveryUnavailable(f"unsupported Play discovery provider: {requested}")


def build_play_search_url(term: str) -> str:
    return f"{_PLAY_ORIGIN}/store/search?q={quote_plus(term.strip())}&c=apps&hl=en&gl=KE"


def build_play_detail_url(package_name: str) -> str:
    return f"{_PLAY_ORIGIN}/store/apps/details?id={quote_plus(package_name)}&hl=en&gl=KE"


def build_serpapi_search_params(term: str) -> dict[str, str]:
    """Build the high-recall Kenya finance query used for indexed Play discovery."""

    return {
        "engine": "google_play",
        "store": "apps",
        "q": term.strip(),
        "apps_category": "FINANCE",
        "gl": "ke",
        "hl": "en",
    }


def parse_play_search_package_ids(page_html: str) -> list[str]:
    decoded = html_lib.unescape(page_html)
    seen: set[str] = set()
    result: list[str] = []
    for package_name in _PACKAGE_RE.findall(decoded):
        if package_name not in seen:
            seen.add(package_name)
            result.append(package_name)
    return result


def parse_serpapi_search_package_ids(payload: dict[str, object]) -> list[str]:
    """Collect Google Play package IDs from SerpApi's structured result sections."""

    seen: set[str] = set()
    result: list[str] = []

    def visit(value: object) -> None:
        if isinstance(value, dict):
            product_id = value.get("product_id")
            if isinstance(product_id, str) and product_id and product_id not in seen:
                seen.add(product_id)
                result.append(product_id)
            for key in ("app_highlight", "organic_results", "items"):
                if key in value:
                    visit(value[key])
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(payload)
    return result


def _serpapi_search_source_url(payload: dict[str, object]) -> str:
    request_params = payload.get("request_params")
    params = request_params if isinstance(request_params, dict) else {}
    query = str(params.get("q") or "loan").strip()
    category = str(params.get("apps_category") or "FINANCE").strip()
    gl = str(params.get("gl") or "ke").strip().lower()
    hl = str(params.get("hl") or "en").strip().lower()
    return (
        "https://serpapi.com/search?engine=google_play&store=apps"
        f"&q={quote_plus(query)}&apps_category={quote_plus(category)}&gl={quote_plus(gl)}&hl={quote_plus(hl)}"
    )


def parse_serpapi_search_items(
    payload: dict[str, object],
    *,
    observed_at: datetime | None = None,
) -> list[PlayAppImportItem]:
    """Normalize useful SerpApi search rows so detail enrichment is optional.

    Google Play search results already expose package ID, app title and author.
    KDR keeps those fields as valid public marketplace evidence instead of
    discarding the entire search when a follow-up product response changes
    shape, omits ``product_info`` or otherwise cannot be enriched.
    """

    when = observed_at or datetime.now(UTC)
    source_url = _serpapi_search_source_url(payload)
    by_package: dict[str, PlayAppImportItem] = {}

    def visit(value: object) -> None:
        if isinstance(value, dict):
            product_id = value.get("product_id")
            title = value.get("title")
            author = value.get("author")
            developer_name = ""
            if isinstance(author, str):
                developer_name = author.strip()
            elif isinstance(author, dict):
                developer_name = str(author.get("name") or "").strip()

            if (
                isinstance(product_id, str)
                and product_id.strip()
                and isinstance(title, str)
                and title.strip()
                and developer_name
                and product_id.strip() not in by_package
            ):
                package_name = product_id.strip()
                raw_link = value.get("link")
                store_url = build_play_detail_url(package_name)
                if isinstance(raw_link, str):
                    parsed = urlparse(raw_link.strip())
                    if parsed.scheme == "https" and parsed.hostname == "play.google.com":
                        store_url = raw_link.strip()
                by_package[package_name] = PlayAppImportItem(
                    package_name=package_name,
                    app_name=title.strip(),
                    developer_name=developer_name,
                    store_url=store_url,
                    category="Finance",
                    source_provider="serpapi-google-play-search-v1",
                    source_url=source_url,
                    observed_at=when,
                )

            for key in ("app_highlight", "organic_results", "items"):
                if key in value:
                    visit(value[key])
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(payload)
    return list(by_package.values())


def _json_ld(page_html: str) -> dict[str, object]:
    for raw in _LD_JSON_RE.findall(page_html):
        try:
            value = json.loads(html_lib.unescape(raw).strip())
        except (json.JSONDecodeError, TypeError):
            continue
        candidates = value if isinstance(value, list) else [value]
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("name"):
                return candidate
    return {}


def _clean_link(value: str) -> str | None:
    value = html_lib.unescape(value).strip()
    if value.startswith("/url?"):
        query = parse_qs(urlparse(value).query)
        value = unquote((query.get("q") or query.get("url") or [""])[0])
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        return None
    return value


def _link_metadata(page_html: str) -> tuple[str | None, str | None]:
    support_email: str | None = None
    privacy_url: str | None = None
    for href, label_html in _LINK_RE.findall(page_html):
        label = _TAG_RE.sub(" ", html_lib.unescape(label_html)).strip().casefold()
        decoded_href = html_lib.unescape(href)
        if decoded_href.lower().startswith("mailto:") and support_email is None:
            support_email = decoded_href[7:].split("?", 1)[0].strip().lower()
        if "privacy" in label and privacy_url is None:
            privacy_url = _clean_link(decoded_href)
    if support_email is None:
        match = _EMAIL_RE.search(html_lib.unescape(page_html))
        support_email = match.group(0).lower() if match else None
    return support_email, privacy_url


def parse_play_detail_html(
    package_name: str,
    page_html: str,
    *,
    observed_at: datetime | None = None,
) -> PlayAppImportItem:
    metadata = _json_ld(page_html)
    author = metadata.get("author")
    developer_name = ""
    if isinstance(author, dict):
        developer_name = str(author.get("name") or "").strip()
    elif isinstance(author, str):
        developer_name = author.strip()
    app_name = str(metadata.get("name") or "").strip()
    if not app_name or not developer_name:
        raise ValueError("Google Play page did not expose a usable app/developer identity")
    support_email, privacy_url = _link_metadata(page_html)
    detail_url = build_play_detail_url(package_name)
    category = metadata.get("applicationCategory")
    installs = metadata.get("numDownloads")
    return PlayAppImportItem(
        package_name=package_name,
        app_name=app_name,
        developer_name=developer_name,
        support_email=support_email,
        privacy_policy_url=privacy_url,
        store_url=detail_url,
        category=str(category) if category else None,
        installs=str(installs) if installs else None,
        source_provider="kdr-google-play-public-html-v1",
        source_url=detail_url,
        observed_at=observed_at or datetime.now(UTC),
    )


def parse_serpapi_product(
    package_name: str,
    payload: dict[str, object],
    *,
    observed_at: datetime | None = None,
) -> PlayAppImportItem:
    product_info = payload.get("product_info")
    if not isinstance(product_info, dict):
        raise ValueError("SerpApi product response did not contain product_info")
    contact = payload.get("developer_contact")
    developer_contact = contact if isinstance(contact, dict) else {}

    title = str(product_info.get("title") or "").strip()
    authors = product_info.get("authors")
    developer_name = ""
    developer_id: str | None = None
    if isinstance(authors, list) and authors:
        first = authors[0]
        if isinstance(first, dict):
            developer_name = str(first.get("name") or "").strip()
            link = first.get("link")
            developer_id = str(link).strip() if link else None
    if not developer_name:
        developer_name = str(developer_contact.get("name") or "").strip()
    if not title or not developer_name:
        raise ValueError("SerpApi product response did not expose a usable app/developer identity")

    website = developer_contact.get("website")
    support_email = developer_contact.get("support_email")
    privacy = developer_contact.get("privacy_policy")
    category = product_info.get("category") or product_info.get("application_category")
    installs = product_info.get("downloads")
    detail_url = build_play_detail_url(package_name)
    source_url = (
        "https://serpapi.com/search?engine=google_play_product&store=apps"
        f"&product_id={quote_plus(package_name)}&gl=ke&hl=en"
    )
    return PlayAppImportItem(
        package_name=package_name,
        app_name=title,
        developer_name=developer_name,
        developer_id=developer_id,
        support_email=str(support_email).strip() if support_email else None,
        developer_website=str(website).strip() if website else None,
        privacy_policy_url=str(privacy).strip() if privacy else None,
        store_url=detail_url,
        category=str(category).strip() if category else None,
        installs=str(installs).strip() if installs else None,
        source_provider="serpapi-google-play-v1",
        source_url=source_url,
        observed_at=observed_at or datetime.now(UTC),
    )


def _fetch_html(client: httpx.Client, url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "play.google.com":
        raise ValueError("Play discovery is restricted to public play.google.com HTTPS pages")
    try:
        response = client.get(
            url,
            headers={"User-Agent": "KenyaDataRights/0.1 public-metadata-research"},
            timeout=15.0,
            follow_redirects=False,
        )
    except httpx.HTTPError as exc:
        raise PlayDiscoveryUnavailable("Google Play request failed") from exc
    if response.status_code in {403, 429}:
        raise PlayDiscoveryUnavailable(
            "Google Play declined the public request; KDR will not bypass anti-bot controls"
        )
    if response.status_code != 200:
        raise PlayDiscoveryUnavailable(f"Google Play returned HTTP {response.status_code}")
    if len(response.content) > _MAX_HTML_BYTES:
        raise PlayDiscoveryUnavailable("Google Play response exceeded the bounded HTML limit")
    content_type = response.headers.get("content-type", "")
    if content_type and "text/html" not in content_type.lower():
        raise PlayDiscoveryUnavailable("Google Play returned an unexpected content type")
    return response.text


def _fetch_serpapi_json(
    client: httpx.Client,
    *,
    api_key: str,
    params: dict[str, str],
) -> dict[str, object]:
    request_params = {**params, "api_key": api_key}
    try:
        response = client.get(
            _SERPAPI_ENDPOINT,
            params=request_params,
            headers={"User-Agent": "KenyaDataRights/0.1 indexed-metadata-research"},
            timeout=20.0,
            follow_redirects=False,
        )
    except httpx.HTTPError as exc:
        raise PlayDiscoveryUnavailable("SerpApi request failed") from exc
    if response.status_code == 429:
        raise PlayDiscoveryUnavailable("SerpApi rate/search quota was reached")
    if response.status_code in {401, 403}:
        raise PlayDiscoveryUnavailable("SerpApi rejected the configured API key")
    if response.status_code != 200:
        raise PlayDiscoveryUnavailable(f"SerpApi returned HTTP {response.status_code}")
    if len(response.content) > _MAX_JSON_BYTES:
        raise PlayDiscoveryUnavailable("SerpApi response exceeded the bounded JSON limit")
    try:
        payload = response.json()
    except ValueError as exc:
        raise PlayDiscoveryUnavailable("SerpApi returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise PlayDiscoveryUnavailable("SerpApi returned an unexpected JSON shape")
    error = payload.get("error")
    if error:
        raise PlayDiscoveryUnavailable(f"SerpApi search failed: {str(error)[:240]}")
    return payload


def _provider_terms(record: dict[str, object]) -> list[str]:
    values = [
        record.get("trading_name"),
        record.get("legal_name"),
        record.get("website_domain"),
    ]
    return list(dict.fromkeys(str(value).strip() for value in values if str(value or "").strip()))


def _append_packages(target: list[str], discovered: list[str], *, limit: int) -> None:
    for package_name in discovered:
        if package_name not in target:
            target.append(package_name)
        if len(target) >= limit:
            break


def _capture_serpapi_search_rows(
    payload: dict[str, object],
    *,
    package_ids: list[str],
    search_items: dict[str, PlayAppImportItem],
    limit: int,
) -> None:
    _append_packages(package_ids, parse_serpapi_search_package_ids(payload), limit=limit)
    allowed = set(package_ids)
    for item in parse_serpapi_search_items(payload):
        if item.package_name in allowed and item.package_name not in search_items:
            search_items[item.package_name] = item


def _rotating_detail_packages(package_ids: list[str], *, start_index: int) -> list[str]:
    if not package_ids:
        return []
    count = min(_MAX_SERPAPI_PRODUCT_ENRICHMENTS_PER_RUN, len(package_ids))
    offset = start_index % len(package_ids)
    return [package_ids[(offset + index) % len(package_ids)] for index in range(count)]


def run_cbk_play_discovery(
    session: Session,
    *,
    max_providers: int = 25,
    max_apps: int = 100,
    client: httpx.Client | None = None,
    start_index: int | None = None,
    provider: str | None = None,
    serpapi_api_key: str | None = None,
) -> PlayDiscoveryResult:
    settings = get_settings()
    api_key = serpapi_api_key if serpapi_api_key is not None else settings.serpapi_api_key
    chosen_provider = selected_discovery_provider(
        provider or settings.play_discovery_provider,
        serpapi_api_key=api_key,
    )

    seeds = build_cbk_discovery_seeds(session)
    records = list(seeds.get("records") or [])
    if not records:
        return PlayDiscoveryResult(
            chosen_provider, 0, 0, 0, 0, 0, 0, ("CBK discovery seeds are unavailable",)
        )

    safe_provider_limit = max(1, min(max_providers, 50))
    safe_app_limit = max(1, min(max_apps, 200))
    if start_index is None:
        start_index = (datetime.now(UTC).date().toordinal() * safe_provider_limit) % len(records)
    selected = [
        records[(start_index + offset) % len(records)]
        for offset in range(min(safe_provider_limit, len(records)))
    ]

    owns_client = client is None
    http_client = client or httpx.Client()
    package_ids: list[str] = []
    serpapi_search_items: dict[str, PlayAppImportItem] = {}
    failures: list[str] = []
    search_requests = 0
    detail_requests = 0
    try:
        # Start with the broad Kenya/English/Finance query proven useful in the
        # SerpApi playground. Keep those search rows as evidence immediately so
        # a later product lookup failure cannot erase a valid marketplace hit.
        if chosen_provider == "serpapi":
            search_requests += 1
            try:
                page = _fetch_serpapi_json(
                    http_client,
                    api_key=api_key or "",
                    params=build_serpapi_search_params("loan"),
                )
                _capture_serpapi_search_rows(
                    page,
                    package_ids=package_ids,
                    search_items=serpapi_search_items,
                    limit=safe_app_limit,
                )
            except PlayDiscoveryUnavailable as exc:
                failures.append(str(exc))

        # Enrich/expand using regulator identity terms only when the broad search
        # did not already fill this bounded run. Provider-specific searches use
        # the same Kenya/Finance localization contract when SerpApi is active.
        for record in selected:
            for term in _provider_terms(record)[:2]:
                if len(package_ids) >= safe_app_limit:
                    break
                search_requests += 1
                try:
                    if chosen_provider == "serpapi":
                        page = _fetch_serpapi_json(
                            http_client,
                            api_key=api_key or "",
                            params=build_serpapi_search_params(term),
                        )
                        _capture_serpapi_search_rows(
                            page,
                            package_ids=package_ids,
                            search_items=serpapi_search_items,
                            limit=safe_app_limit,
                        )
                    else:
                        page_html = _fetch_html(http_client, build_play_search_url(term))
                        discovered = parse_play_search_package_ids(page_html)
                        _append_packages(package_ids, discovered, limit=safe_app_limit)
                except PlayDiscoveryUnavailable as exc:
                    failures.append(str(exc))
                    continue
            if len(package_ids) >= safe_app_limit:
                break

        # Product detail is enrichment, not a prerequisite. Start from the
        # normalized search rows and overwrite each package with richer product
        # metadata only when that follow-up response parses successfully. SerpApi
        # enrichment is deliberately capped and rotated to conserve search quota.
        parsed_by_package: dict[str, PlayAppImportItem] = {
            package_name: serpapi_search_items[package_name]
            for package_name in package_ids
            if package_name in serpapi_search_items
        }
        detail_package_ids = package_ids
        if chosen_provider == "serpapi":
            detail_package_ids = _rotating_detail_packages(
                package_ids,
                start_index=start_index,
            )

        for package_name in detail_package_ids:
            detail_requests += 1
            try:
                if chosen_provider == "serpapi":
                    detail_payload = _fetch_serpapi_json(
                        http_client,
                        api_key=api_key or "",
                        params={
                            "engine": "google_play_product",
                            "store": "apps",
                            "product_id": package_name,
                            "gl": "ke",
                            "hl": "en",
                        },
                    )
                    parsed_by_package[package_name] = parse_serpapi_product(
                        package_name,
                        detail_payload,
                    )
                else:
                    detail_html = _fetch_html(http_client, build_play_detail_url(package_name))
                    parsed_by_package[package_name] = parse_play_detail_html(
                        package_name,
                        detail_html,
                    )
            except (PlayDiscoveryUnavailable, ValueError) as exc:
                failures.append(f"{package_name}: {exc}")

        registry = AppRegistryRepository(session)
        apps_ingested = 0
        ownership_candidates = 0
        for package_name in package_ids:
            item = parsed_by_package.get(package_name)
            if item is None:
                continue
            app = registry.ingest_play(item)
            links = registry.generate_candidates(app.id)
            apps_ingested += 1
            ownership_candidates += len(links)

        relationship_edges = sync_app_ownership_relationships(session)
        return PlayDiscoveryResult(
            provider=chosen_provider,
            providers_considered=len(selected),
            search_requests=search_requests,
            detail_requests=detail_requests,
            apps_ingested=apps_ingested,
            ownership_candidates=ownership_candidates,
            relationship_edges=relationship_edges,
            failures=tuple(dict.fromkeys(failures))[:20],
        )
    finally:
        if owns_client:
            http_client.close()
