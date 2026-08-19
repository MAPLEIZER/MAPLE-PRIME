from __future__ import annotations

from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from app.db.repositories import AppRegistryRepository
from app.schemas.apps import PlayAppImportItem
from app.services.app_discovery import build_cbk_discovery_seeds
from app.services.play_store_discovery import (
    PlayDiscoveryResult,
    PlayDiscoveryUnavailable,
    _capture_serpapi_search_rows,
    _fetch_serpapi_json,
    _provider_terms,
    _rotating_detail_packages,
    parse_serpapi_product,
)
from app.services.relationship_backfill import sync_app_ownership_relationships


def build_serpapi_query_params(term: str) -> dict[str, str]:
    """SerpApi Google Play keyword search.

    SerpApi documents query search (`q`) and category search (`apps_category`)
    as distinct search modes. Do not combine them: that produced HTTP 400 on
    a valid user account.
    """

    return {
        "engine": "google_play",
        "store": "apps",
        "q": term.strip(),
        "gl": "ke",
        "hl": "en",
    }


def build_serpapi_finance_category_params() -> dict[str, str]:
    return {
        "engine": "google_play",
        "store": "apps",
        "apps_category": "FINANCE",
        "gl": "ke",
        "hl": "en",
    }


def run_cbk_serpapi_play_discovery(
    session: Session,
    *,
    max_providers: int = 5,
    max_apps: int = 15,
    client: httpx.Client | None = None,
    start_index: int | None = None,
    api_key: str,
) -> PlayDiscoveryResult:
    if not api_key.strip():
        raise PlayDiscoveryUnavailable("SerpApi is selected but its API key is missing")

    seeds = build_cbk_discovery_seeds(session)
    records = list(seeds.get("records") or [])
    if not records:
        return PlayDiscoveryResult("serpapi", 0, 0, 0, 0, 0, 0, ("CBK discovery seeds are unavailable",))

    safe_provider_limit = max(1, min(max_providers, 50))
    safe_app_limit = max(1, min(max_apps, 200))
    if start_index is None:
        start_index = (datetime.now(UTC).date().toordinal() * safe_provider_limit) % len(records)
    selected = [records[(start_index + offset) % len(records)] for offset in range(min(safe_provider_limit, len(records)))]

    owns_client = client is None
    http_client = client or httpx.Client()
    package_ids: list[str] = []
    search_items: dict[str, PlayAppImportItem] = {}
    failures: list[str] = []
    search_requests = 0
    detail_requests = 0

    def capture(params: dict[str, str]) -> None:
        nonlocal search_requests
        search_requests += 1
        page = _fetch_serpapi_json(http_client, api_key=api_key, params=params)
        _capture_serpapi_search_rows(
            page,
            package_ids=package_ids,
            search_items=search_items,
            limit=safe_app_limit,
        )

    try:
        # First use the high-recall Kenya keyword query. This is a q-search only;
        # apps_category is intentionally not mixed into it because SerpApi treats
        # category browsing as a separate request mode.
        try:
            capture(build_serpapi_query_params("loan"))
        except PlayDiscoveryUnavailable as exc:
            failures.append(str(exc))

        # Add a Finance category browse only if the keyword query did not fill
        # the bounded run. This gives us category recall without invalid params.
        if len(package_ids) < safe_app_limit:
            try:
                capture(build_serpapi_finance_category_params())
            except PlayDiscoveryUnavailable as exc:
                failures.append(str(exc))

        for record in selected:
            if len(package_ids) >= safe_app_limit:
                break
            for term in _provider_terms(record)[:2]:
                if len(package_ids) >= safe_app_limit:
                    break
                try:
                    capture(build_serpapi_query_params(term))
                except PlayDiscoveryUnavailable as exc:
                    failures.append(str(exc))

        parsed_by_package: dict[str, PlayAppImportItem] = {
            package_name: search_items[package_name]
            for package_name in package_ids
            if package_name in search_items
        }

        for package_name in _rotating_detail_packages(package_ids, start_index=start_index):
            detail_requests += 1
            try:
                detail_payload = _fetch_serpapi_json(
                    http_client,
                    api_key=api_key,
                    params={
                        "engine": "google_play_product",
                        "store": "apps",
                        "product_id": package_name,
                        "gl": "ke",
                        "hl": "en",
                    },
                )
                parsed_by_package[package_name] = parse_serpapi_product(package_name, detail_payload)
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
            provider="serpapi",
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
