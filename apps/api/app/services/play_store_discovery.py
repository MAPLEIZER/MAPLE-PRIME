from __future__ import annotations

import html as html_lib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from sqlalchemy.orm import Session

from app.db.repositories import AppRegistryRepository
from app.schemas.apps import PlayAppImportItem
from app.services.app_discovery import build_cbk_discovery_seeds
from app.services.relationship_backfill import sync_app_ownership_relationships

_PLAY_ORIGIN = "https://play.google.com"
_MAX_HTML_BYTES = 2 * 1024 * 1024
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
    providers_considered: int
    search_requests: int
    detail_requests: int
    apps_ingested: int
    ownership_candidates: int
    relationship_edges: int
    failures: tuple[str, ...] = field(default_factory=tuple)


def build_play_search_url(term: str) -> str:
    return f"{_PLAY_ORIGIN}/store/search?q={quote_plus(term.strip())}&c=apps&hl=en&gl=KE"


def build_play_detail_url(package_name: str) -> str:
    return f"{_PLAY_ORIGIN}/store/apps/details?id={quote_plus(package_name)}&hl=en&gl=KE"


def parse_play_search_package_ids(page_html: str) -> list[str]:
    decoded = html_lib.unescape(page_html)
    seen: set[str] = set()
    result: list[str] = []
    for package_name in _PACKAGE_RE.findall(decoded):
        if package_name not in seen:
            seen.add(package_name)
            result.append(package_name)
    return result


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


def _provider_terms(record: dict[str, object]) -> list[str]:
    values = [
        record.get("trading_name"),
        record.get("legal_name"),
        record.get("website_domain"),
    ]
    return list(dict.fromkeys(str(value).strip() for value in values if str(value or "").strip()))


def run_cbk_play_discovery(
    session: Session,
    *,
    max_providers: int = 25,
    max_apps: int = 100,
    client: httpx.Client | None = None,
    start_index: int | None = None,
) -> PlayDiscoveryResult:
    seeds = build_cbk_discovery_seeds(session)
    records = list(seeds.get("records") or [])
    if not records:
        return PlayDiscoveryResult(0, 0, 0, 0, 0, 0, ("CBK discovery seeds are unavailable",))

    safe_provider_limit = max(1, min(max_providers, 50))
    safe_app_limit = max(1, min(max_apps, 200))
    if start_index is None:
        start_index = (datetime.now(UTC).date().toordinal() * safe_provider_limit) % len(records)
    selected = [records[(start_index + offset) % len(records)] for offset in range(min(safe_provider_limit, len(records)))]

    owns_client = client is None
    http_client = client or httpx.Client()
    registry = AppRegistryRepository(session)
    package_ids: list[str] = []
    failures: list[str] = []
    search_requests = 0
    detail_requests = 0
    try:
        for record in selected:
            for term in _provider_terms(record)[:2]:
                if len(package_ids) >= safe_app_limit:
                    break
                search_requests += 1
                try:
                    page = _fetch_html(http_client, build_play_search_url(term))
                except PlayDiscoveryUnavailable as exc:
                    failures.append(str(exc))
                    continue
                for package_name in parse_play_search_package_ids(page):
                    if package_name not in package_ids:
                        package_ids.append(package_name)
                    if len(package_ids) >= safe_app_limit:
                        break
            if len(package_ids) >= safe_app_limit:
                break

        apps_ingested = 0
        ownership_candidates = 0
        for package_name in package_ids:
            detail_requests += 1
            try:
                detail_html = _fetch_html(http_client, build_play_detail_url(package_name))
                item = parse_play_detail_html(package_name, detail_html)
            except (PlayDiscoveryUnavailable, ValueError) as exc:
                failures.append(str(exc))
                continue
            app = registry.ingest_play(item)
            links = registry.generate_candidates(app.id)
            apps_ingested += 1
            ownership_candidates += len(links)

        relationship_edges = sync_app_ownership_relationships(session)
        return PlayDiscoveryResult(
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
