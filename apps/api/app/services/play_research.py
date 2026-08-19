from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Literal

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import AppStoreObservation, MarketplaceApp
from app.db.repositories import AppRegistryRepository
from app.schemas.apps import PlayAppImportItem
from app.services.play_discovery_provider import resolve_play_provider
from app.services.play_store_discovery import (
    PlayDiscoveryUnavailable,
    _fetch_serpapi_json,
    parse_serpapi_product,
)
from app.services.relationship_backfill import sync_app_ownership_relationships
from app.services.serpapi_play_discovery import (
    build_serpapi_finance_category_params,
    build_serpapi_query_params,
)
from app.services.serpapi_research_parser import parse_serpapi_research_items
from app.services.talordata_play_discovery import (
    _fetch_talordata_json,
    build_talordata_search_payload,
    parse_talordata_search_items,
)

ResearchMode = Literal["category", "query", "hybrid"]

DEFAULT_RESEARCH_QUERIES: tuple[str, ...] = (
    "loan",
    "credit",
    "mkopo",
    "advance",
    "salary advance",
    "cash loan",
    "mobile loan",
    "quick loan",
    "emergency loan",
    "digital credit",
    "microloan",
    "borrow",
    "pesa",
)


@dataclass(frozen=True)
class PlayResearchOptions:
    provider: str = "auto"
    mode: ResearchMode = "category"
    queries: tuple[str, ...] = ()
    max_pages: int = 5
    max_apps: int = 250
    enrich_limit: int = 0
    skip_existing: bool = True
    match_ownership: bool = False


def normalize_research_queries(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = " ".join(str(raw).split()).strip()
        if not value:
            continue
        value = value[:80]
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
        if len(result) >= 20:
            break
    return tuple(result)


def _next_serpapi_page_token(payload: dict[str, object]) -> str | None:
    pagination = payload.get("serpapi_pagination")
    if not isinstance(pagination, dict):
        return None
    token = pagination.get("next_page_token")
    return token.strip() if isinstance(token, str) and token.strip() else None


def _existing_apps(session: Session, package_names: list[str]) -> dict[str, MarketplaceApp]:
    if not package_names:
        return {}
    statement = select(MarketplaceApp).where(
        MarketplaceApp.store == "google_play",
        MarketplaceApp.package_name.in_(package_names),
    )
    return {item.package_name: item for item in session.scalars(statement)}


def _existing_emails(session: Session) -> set[str]:
    statement = select(func.lower(AppStoreObservation.support_email)).where(
        AppStoreObservation.support_email.is_not(None)
    )
    return {str(value).strip().lower() for value in session.scalars(statement) if str(value or "").strip()}


def _merge_existing_contact(
    item: PlayAppImportItem,
    observation: AppStoreObservation | None,
) -> PlayAppImportItem:
    if observation is None:
        return item
    updates: dict[str, object] = {}
    for field in (
        "support_email",
        "developer_website",
        "privacy_policy_url",
        "developer_id",
        "installs",
    ):
        if getattr(item, field) is None:
            value = getattr(observation, field, None)
            if value:
                updates[field] = value
    return item.model_copy(update=updates) if updates else item


def _add_discovered(
    *,
    items: list[PlayAppImportItem],
    label: str,
    by_package: dict[str, PlayAppImportItem],
    matched_by: dict[str, set[str]],
    max_apps: int,
) -> int:
    duplicates = 0
    for item in items:
        matched_by.setdefault(item.package_name, set()).add(label)
        if item.package_name in by_package:
            duplicates += 1
            continue
        if len(by_package) >= max_apps:
            break
        by_package[item.package_name] = item
    return duplicates


def _collect_serpapi(
    *,
    client: httpx.Client,
    api_key: str,
    options: PlayResearchOptions,
    queries: tuple[str, ...],
) -> tuple[dict[str, PlayAppImportItem], dict[str, set[str]], int, int, int, list[str]]:
    queue: deque[tuple[str, dict[str, str]]] = deque()
    if options.mode in {"category", "hybrid"}:
        queue.append(("Finance category", build_serpapi_finance_category_params()))
    if options.mode in {"query", "hybrid"}:
        for query in queries:
            queue.append((f"query:{query}", build_serpapi_query_params(query)))

    by_package: dict[str, PlayAppImportItem] = {}
    matched_by: dict[str, set[str]] = {}
    failures: list[str] = []
    search_requests = 0
    pages_fetched = 0
    duplicate_packages = 0

    while queue and search_requests < options.max_pages and len(by_package) < options.max_apps:
        label, params = queue.popleft()
        search_requests += 1
        try:
            payload = _fetch_serpapi_json(client, api_key=api_key, params=params)
        except PlayDiscoveryUnavailable as exc:
            failures.append(f"{label}: {exc}")
            continue
        pages_fetched += 1
        duplicate_packages += _add_discovered(
            items=parse_serpapi_research_items(payload, params=params),
            label=label,
            by_package=by_package,
            matched_by=matched_by,
            max_apps=options.max_apps,
        )
        token = _next_serpapi_page_token(payload)
        if token and search_requests + len(queue) < options.max_pages and len(by_package) < options.max_apps:
            continuation = {key: value for key, value in params.items() if key != "next_page_token"}
            continuation["next_page_token"] = token
            queue.append((label, continuation))

    return by_package, matched_by, search_requests, pages_fetched, duplicate_packages, failures


def _collect_talordata(
    *,
    client: httpx.Client,
    api_key: str,
    endpoint: str,
    options: PlayResearchOptions,
    queries: tuple[str, ...],
) -> tuple[dict[str, PlayAppImportItem], dict[str, set[str]], int, int, int, list[str]]:
    requests: list[tuple[str, str, bool]] = []
    if options.mode in {"category", "hybrid"}:
        requests.append(("Finance category", "", True))
    if options.mode in {"query", "hybrid"}:
        requests.extend((f"query:{query}", query, False) for query in queries)

    by_package: dict[str, PlayAppImportItem] = {}
    matched_by: dict[str, set[str]] = {}
    failures: list[str] = []
    search_requests = 0
    pages_fetched = 0
    duplicate_packages = 0

    for label, term, category_only in requests[: options.max_pages]:
        if len(by_package) >= options.max_apps:
            break
        search_requests += 1
        try:
            payload = _fetch_talordata_json(
                client,
                api_key=api_key,
                endpoint=endpoint,
                payload=build_talordata_search_payload(term, category_only=category_only),
            )
        except PlayDiscoveryUnavailable as exc:
            failures.append(f"{label}: {exc}")
            continue
        pages_fetched += 1
        duplicate_packages += _add_discovered(
            items=parse_talordata_search_items(
                payload,
                term=term,
                category_only=category_only,
            ),
            label=label,
            by_package=by_package,
            matched_by=matched_by,
            max_apps=options.max_apps,
        )

    return by_package, matched_by, search_requests, pages_fetched, duplicate_packages, failures


def run_play_research(
    session: Session,
    *,
    options: PlayResearchOptions,
    settings: Settings | None = None,
    client: httpx.Client | None = None,
) -> dict[str, object]:
    current = settings or get_settings()
    queries = normalize_research_queries(options.queries)
    if options.mode in {"query", "hybrid"} and not queries:
        queries = DEFAULT_RESEARCH_QUERIES[:6]

    resolved = resolve_play_provider(
        options.provider,
        talordata_api_key=current.talordata_api_key,
        serpapi_api_key=current.serpapi_api_key,
    )
    if resolved.provider == "public_html":
        raise PlayDiscoveryUnavailable(
            "The research console requires TalorData or SerpApi.com; public HTML remains available through the small legacy discovery run."
        )

    safe_options = PlayResearchOptions(
        provider=options.provider,
        mode=options.mode,
        queries=queries,
        max_pages=max(1, min(options.max_pages, 25)),
        max_apps=max(1, min(options.max_apps, 500)),
        enrich_limit=max(0, min(options.enrich_limit, 100)),
        skip_existing=options.skip_existing,
        match_ownership=options.match_ownership,
    )

    owns_client = client is None
    http_client = client or httpx.Client()
    try:
        if resolved.provider == "serpapi":
            (
                by_package,
                matched_by,
                search_requests,
                pages_fetched,
                duplicate_packages,
                failures,
            ) = _collect_serpapi(
                client=http_client,
                api_key=resolved.serpapi_api_key or "",
                options=safe_options,
                queries=queries,
            )
        else:
            (
                by_package,
                matched_by,
                search_requests,
                pages_fetched,
                duplicate_packages,
                failures,
            ) = _collect_talordata(
                client=http_client,
                api_key=resolved.talordata_api_key or "",
                endpoint=current.talordata_serp_endpoint,
                options=safe_options,
                queries=queries,
            )

        package_names = list(by_package)
        existing_by_package = _existing_apps(session, package_names)
        registry = AppRegistryRepository(session)

        # Product calls are deliberately optional and, by default, target only
        # packages that are not already in the local registry. This lets a large
        # category crawl enumerate apps cheaply before spending credits on email
        # and website enrichment.
        detail_requests = 0
        if resolved.provider == "serpapi" and safe_options.enrich_limit:
            candidates = [
                package_name
                for package_name in package_names
                if not (safe_options.skip_existing and package_name in existing_by_package)
            ][: safe_options.enrich_limit]
            for package_name in candidates:
                detail_requests += 1
                try:
                    payload = _fetch_serpapi_json(
                        http_client,
                        api_key=resolved.serpapi_api_key or "",
                        params={
                            "engine": "google_play_product",
                            "store": "apps",
                            "product_id": package_name,
                            "gl": "ke",
                            "hl": "en",
                        },
                    )
                    by_package[package_name] = parse_serpapi_product(package_name, payload)
                except (PlayDiscoveryUnavailable, ValueError) as exc:
                    failures.append(f"{package_name}: {exc}")

        existing_email_values = _existing_emails(session)
        seen_new_emails: set[str] = set()
        rows: list[dict[str, object]] = []
        new_apps = 0
        existing_apps = 0
        skipped_existing_apps = 0
        apps_ingested = 0
        ownership_candidates = 0
        emails_found = 0
        new_unique_emails = 0
        existing_email_hits = 0
        duplicate_emails_in_run = 0

        for package_name, discovered_item in by_package.items():
            existing = existing_by_package.get(package_name)
            existing_observation = registry.latest_observation(existing.id) if existing is not None else None
            item = _merge_existing_contact(discovered_item, existing_observation)
            was_ingested = False

            if existing is None:
                new_apps += 1
                app = registry.ingest_play(item)
                apps_ingested += 1
                was_ingested = True
                database_status = "new"
            else:
                existing_apps += 1
                app = existing
                if safe_options.skip_existing:
                    skipped_existing_apps += 1
                    database_status = "existing"
                else:
                    app = registry.ingest_play(item)
                    apps_ingested += 1
                    was_ingested = True
                    database_status = "refreshed"

            if safe_options.match_ownership and was_ingested:
                links = registry.generate_candidates(app.id)
                ownership_candidates += len(links)

            email = (item.support_email or "").strip().lower() or None
            if email:
                emails_found += 1
                if email in existing_email_values:
                    email_status = "existing"
                    existing_email_hits += 1
                elif email in seen_new_emails:
                    email_status = "duplicate_in_run"
                    duplicate_emails_in_run += 1
                else:
                    email_status = "new"
                    new_unique_emails += 1
                    seen_new_emails.add(email)
            else:
                email_status = "none"

            rows.append(
                {
                    "package_name": package_name,
                    "app_name": item.app_name,
                    "developer_name": item.developer_name,
                    "support_email": email,
                    "developer_website": item.developer_website,
                    "privacy_policy_url": item.privacy_policy_url,
                    "store_url": item.store_url,
                    "category": item.category,
                    "installs": item.installs,
                    "database_status": database_status,
                    "email_status": email_status,
                    "matched_by": sorted(matched_by.get(package_name, set())),
                    "source_provider": item.source_provider,
                }
            )

        relationship_edges = (
            sync_app_ownership_relationships(session)
            if safe_options.match_ownership and apps_ingested
            else 0
        )
        rows.sort(
            key=lambda row: (
                0 if row["database_status"] == "new" else 1,
                str(row["app_name"]).casefold(),
                str(row["package_name"]),
            )
        )

        return {
            "provider": resolved.provider,
            "mode": safe_options.mode,
            "queries": list(queries),
            "search_requests": search_requests,
            "pages_fetched": pages_fetched,
            "detail_requests": detail_requests,
            "unique_apps_discovered": len(by_package),
            "duplicate_packages_skipped": duplicate_packages,
            "new_apps": new_apps,
            "existing_apps": existing_apps,
            "skipped_existing_apps": skipped_existing_apps,
            "apps_ingested": apps_ingested,
            "emails_found": emails_found,
            "new_unique_emails": new_unique_emails,
            "existing_email_hits": existing_email_hits,
            "duplicate_emails_in_run": duplicate_emails_in_run,
            "ownership_candidates": ownership_candidates,
            "relationship_edges": relationship_edges,
            "failures": list(dict.fromkeys(failures))[:30],
            "results": rows,
        }
    finally:
        if owns_client:
            http_client.close()
