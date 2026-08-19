from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlencode, urlparse

from app.schemas.apps import PlayAppImportItem
from app.services.play_store_discovery import build_play_detail_url


def serpapi_research_source_url(params: dict[str, str]) -> str:
    """Build a redacted search URL without the private API key.

    Pagination tokens are deliberately omitted from the persisted source URL to
    keep it bounded; KDR records the research run/page counts separately.
    """

    allowed = {
        key: value
        for key, value in params.items()
        if key in {"engine", "store", "q", "apps_category", "gl", "hl", "chart"}
        and value
    }
    return f"https://serpapi.com/search?{urlencode(allowed)}"


def _developer_name(value: dict[str, object]) -> str:
    for key in ("author", "developer", "developer_name"):
        raw = value.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        if isinstance(raw, dict):
            name = raw.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    return ""


def parse_serpapi_research_items(
    payload: dict[str, object],
    *,
    params: dict[str, str],
    observed_at: datetime | None = None,
) -> list[PlayAppImportItem]:
    """Normalize app-like rows from any SerpApi Google Play result section.

    Category pages can expose apps in organic rows or top-chart structures. A
    generic bounded tree walk lets the research console retain both without
    coupling the importer to one presentation shape.
    """

    when = observed_at or datetime.now(UTC)
    source_url = serpapi_research_source_url(params)
    category_search = params.get("apps_category") == "FINANCE"
    source_provider = (
        "serpapi-google-play-category-v1"
        if category_search
        else "serpapi-google-play-query-v1"
    )
    by_package: dict[str, PlayAppImportItem] = {}

    def visit(value: object) -> None:
        if isinstance(value, dict):
            package_name = value.get("product_id") or value.get("package_name")
            title = value.get("title") or value.get("app_name") or value.get("name")
            developer = _developer_name(value)
            if (
                isinstance(package_name, str)
                and "." in package_name
                and isinstance(title, str)
                and title.strip()
                and developer
                and package_name.strip() not in by_package
            ):
                package = package_name.strip()
                raw_link = value.get("link") or value.get("store_url") or value.get("url")
                store_url = build_play_detail_url(package)
                if isinstance(raw_link, str):
                    parsed = urlparse(raw_link.strip())
                    if parsed.scheme == "https" and parsed.hostname == "play.google.com":
                        store_url = raw_link.strip()
                raw_category = value.get("category")
                category = str(raw_category).strip() if raw_category else ("Finance" if category_search else None)
                downloads = value.get("downloads") or value.get("installs")
                by_package[package] = PlayAppImportItem(
                    package_name=package,
                    app_name=title.strip(),
                    developer_name=developer,
                    store_url=store_url,
                    category=category,
                    installs=str(downloads).strip() if downloads else None,
                    source_provider=source_provider,
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
