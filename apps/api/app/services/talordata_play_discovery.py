from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import quote_plus, urlparse

import httpx
from sqlalchemy.orm import Session

from app.db.repositories import AppRegistryRepository
from app.schemas.apps import PlayAppImportItem
from app.services.app_discovery import build_cbk_discovery_seeds
from app.services.play_store_discovery import (
    PlayDiscoveryResult,
    PlayDiscoveryUnavailable,
    build_play_detail_url,
)
from app.services.relationship_backfill import sync_app_ownership_relationships

_DEFAULT_ENDPOINT = "https://api.talordata.com/accounts/v1/serp/get_serp_data"
_MAX_JSON_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class TalorDataRequest:
    term: str
    category_only: bool = False


def build_talordata_search_payload(term: str, *, category_only: bool = False) -> dict[str, str]:
    """Build a TalorData Google Play request localized to Kenya.

    TalorData's SERP API uses a provider-specific POST/Bearer transport. Keep
    keyword and category discovery explicit so KDR can adapt if their Google
    Play vertical evolves without changing the normalized app registry.
    """

    payload = {
        "engine": "google_play",
        "store": "apps",
        "gl": "ke",
        "hl": "en",
        "json": "1",
    }
    if category_only:
        payload["apps_category"] = "FINANCE"
    else:
        payload["q"] = term.strip()
        payload["apps_category"] = "FINANCE"
    return payload


def _talordata_source_url(term: str, *, category_only: bool = False) -> str:
    if category_only:
        return "https://dashboard.talordata.com/scraping/serp-api/statistics#google-play-finance-ke"
    return (
        "https://dashboard.talordata.com/scraping/serp-api/statistics"
        f"#google-play-ke-{quote_plus(term.strip())}"
    )


def _candidate_package(value: dict[str, object]) -> str | None:
    for key in ("product_id", "package_name", "app_id", "id"):
        raw = value.get(key)
        if isinstance(raw, str) and "." in raw and " " not in raw:
            return raw.strip()
    for key in ("link", "url", "store_url"):
        raw = value.get(key)
        if not isinstance(raw, str):
            continue
        parsed = urlparse(raw)
        if parsed.hostname != "play.google.com":
            continue
        query = dict(part.split("=", 1) for part in parsed.query.split("&") if "=" in part)
        package_name = query.get("id")
        if package_name:
            return package_name.strip()
    return None


def _developer_name(value: dict[str, object]) -> str:
    for key in ("developer_name", "developer", "author"):
        raw = value.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        if isinstance(raw, dict):
            name = raw.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    return ""


def parse_talordata_search_items(
    payload: dict[str, object],
    *,
    term: str,
    category_only: bool = False,
    observed_at: datetime | None = None,
) -> list[PlayAppImportItem]:
    """Normalize TalorData Google Play rows using a deliberately tolerant walker."""

    when = observed_at or datetime.now(UTC)
    source_url = _talordata_source_url(term, category_only=category_only)
    by_package: dict[str, PlayAppImportItem] = {}

    def visit(value: object) -> None:
        if isinstance(value, dict):
            package_name = _candidate_package(value)
            title = value.get("title") or value.get("name") or value.get("app_name")
            developer = _developer_name(value)
            if (
                package_name
                and isinstance(title, str)
                and title.strip()
                and developer
                and package_name not in by_package
            ):
                raw_link = value.get("link") or value.get("url") or value.get("store_url")
                store_url = build_play_detail_url(package_name)
                if isinstance(raw_link, str):
                    parsed = urlparse(raw_link.strip())
                    if parsed.scheme == "https" and parsed.hostname == "play.google.com":
                        store_url = raw_link.strip()
                by_package[package_name] = PlayAppImportItem(
                    package_name=package_name,
                    app_name=title.strip(),
                    developer_name=developer,
                    store_url=store_url,
                    category="Finance",
                    source_provider="talordata-google-play-search-v1",
                    source_url=source_url,
                    observed_at=when,
                )
            for child in value.values():
                if isinstance(child, (dict, list)):
                    visit(child)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(payload)
    return list(by_package.values())


def _fetch_talordata_json(
    client: httpx.Client,
    *,
    api_key: str,
    endpoint: str,
    payload: dict[str, str],
) -> dict[str, object]:
    try:
        response = client.post(
            endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "KenyaDataRights/0.1 indexed-metadata-research",
            },
            timeout=30.0,
            follow_redirects=False,
        )
    except httpx.HTTPError as exc:
        raise PlayDiscoveryUnavailable("TalorData request failed") from exc

    if response.status_code == 401:
        raise PlayDiscoveryUnavailable("TalorData rejected the configured SERP API token")
    if response.status_code == 403:
        raise PlayDiscoveryUnavailable("TalorData recognized the request but denied SERP API access")
    if response.status_code == 429:
        raise PlayDiscoveryUnavailable("TalorData rate/search quota was reached")
    if response.status_code != 200:
        detail = response.text.strip().replace("\n", " ")[:200]
        suffix = f": {detail}" if detail else ""
        raise PlayDiscoveryUnavailable(f"TalorData returned HTTP {response.status_code}{suffix}")
    if len(response.content) > _MAX_JSON_BYTES:
        raise PlayDiscoveryUnavailable("TalorData response exceeded the bounded JSON limit")
    try:
        result = response.json()
    except ValueError as exc:
        raise PlayDiscoveryUnavailable("TalorData returned invalid JSON") from exc
    if not isinstance(result, dict):
        raise PlayDiscoveryUnavailable("TalorData returned an unexpected JSON shape")
    return result


def _provider_terms(record: dict[str, object]) -> list[str]:
    values = [record.get("trading_name"), record.get("legal_name"), record.get("website_domain")]
    return list(dict.fromkeys(str(value).strip() for value in values if str(value or "").strip()))


def run_cbk_talordata_play_discovery(
    session: Session,
    *,
    max_providers: int = 5,
    max_apps: int = 15,
    client: httpx.Client | None = None,
    start_index: int | None = None,
    api_key: str,
    endpoint: str = _DEFAULT_ENDPOINT,
) -> PlayDiscoveryResult:
    if not api_key.strip():
        raise PlayDiscoveryUnavailable("TalorData is selected but its SERP API token is missing")

    seeds = build_cbk_discovery_seeds(session)
    records = list(seeds.get("records") or [])
    if not records:
        return PlayDiscoveryResult("talordata", 0, 0, 0, 0, 0, 0, ("CBK discovery seeds are unavailable",))

    safe_provider_limit = max(1, min(max_providers, 50))
    safe_app_limit = max(1, min(max_apps, 200))
    if start_index is None:
        start_index = (datetime.now(UTC).date().toordinal() * safe_provider_limit) % len(records)
    selected = [records[(start_index + offset) % len(records)] for offset in range(min(safe_provider_limit, len(records)))]

    owns_client = client is None
    http_client = client or httpx.Client()
    by_package: dict[str, PlayAppImportItem] = {}
    failures: list[str] = []
    search_requests = 0
    try:
        requests_to_run = [TalorDataRequest("loan")]
        for record in selected:
            for term in _provider_terms(record)[:2]:
                requests_to_run.append(TalorDataRequest(term))

        for request in requests_to_run:
            if len(by_package) >= safe_app_limit:
                break
            search_requests += 1
            try:
                payload = _fetch_talordata_json(
                    http_client,
                    api_key=api_key,
                    endpoint=endpoint,
                    payload=build_talordata_search_payload(
                        request.term,
                        category_only=request.category_only,
                    ),
                )
                for item in parse_talordata_search_items(
                    payload,
                    term=request.term,
                    category_only=request.category_only,
                ):
                    by_package.setdefault(item.package_name, item)
                    if len(by_package) >= safe_app_limit:
                        break
            except PlayDiscoveryUnavailable as exc:
                failures.append(str(exc))

        registry = AppRegistryRepository(session)
        apps_ingested = 0
        ownership_candidates = 0
        for item in list(by_package.values())[:safe_app_limit]:
            app = registry.ingest_play(item)
            links = registry.generate_candidates(app.id)
            apps_ingested += 1
            ownership_candidates += len(links)

        relationship_edges = sync_app_ownership_relationships(session)
        return PlayDiscoveryResult(
            provider="talordata",
            providers_considered=len(selected),
            search_requests=search_requests,
            detail_requests=0,
            apps_ingested=apps_ingested,
            ownership_candidates=ownership_candidates,
            relationship_edges=relationship_edges,
            failures=tuple(dict.fromkeys(failures))[:20],
        )
    finally:
        if owns_client:
            http_client.close()
