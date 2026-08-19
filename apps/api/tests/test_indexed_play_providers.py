from datetime import UTC, datetime

from app.services.play_discovery_provider import resolve_play_provider
from app.services.serpapi_play_discovery import (
    build_serpapi_finance_category_params,
    build_serpapi_query_params,
)
from app.services.talordata_play_discovery import (
    build_talordata_search_payload,
    parse_talordata_search_items,
)


def test_serpapi_keyword_and_category_are_distinct_google_play_modes() -> None:
    query = build_serpapi_query_params("loan")
    category = build_serpapi_finance_category_params()

    assert query == {
        "engine": "google_play",
        "store": "apps",
        "q": "loan",
        "gl": "ke",
        "hl": "en",
    }
    assert "apps_category" not in query
    assert category == {
        "engine": "google_play",
        "store": "apps",
        "apps_category": "FINANCE",
        "gl": "ke",
        "hl": "en",
    }
    assert "q" not in category


def test_provider_resolver_keeps_talordata_and_serpapi_separate() -> None:
    talor = resolve_play_provider(
        "talordata",
        talordata_api_key="sk_talor",
        serpapi_api_key="serp-key",
    )
    serp = resolve_play_provider(
        "serpapi",
        talordata_api_key="sk_talor",
        serpapi_api_key="serp-key",
    )

    assert talor.provider == "talordata"
    assert talor.talordata_api_key == "sk_talor"
    assert serp.provider == "serpapi"
    assert serp.serpapi_api_key == "serp-key"


def test_auto_provider_prefers_explicit_talordata_then_serpapi() -> None:
    both = resolve_play_provider(
        "auto",
        talordata_api_key="sk_talor",
        serpapi_api_key="serp-key",
    )
    serp_only = resolve_play_provider(
        "auto",
        talordata_api_key=None,
        serpapi_api_key="serp-key",
    )
    assert both.provider == "talordata"
    assert serp_only.provider == "serpapi"


def test_talordata_request_uses_kenya_finance_google_play_contract() -> None:
    payload = build_talordata_search_payload("loan")
    assert payload["engine"] == "google_play"
    assert payload["q"] == "loan"
    assert payload["apps_category"] == "FINANCE"
    assert payload["gl"] == "ke"
    assert payload["hl"] == "en"


def test_talordata_parser_accepts_playground_like_rows_without_exposing_token() -> None:
    payload = {
        "organic_results": [
            {
                "items": [
                    {
                        "title": "Branch: Loans & Mobile Banking",
                        "product_id": "com.branch_international.branch.branch_demo_android",
                        "author": "Branch International Financial Services Limited",
                        "link": "https://play.google.com/store/apps/details?id=com.branch_international.branch.branch_demo_android",
                    },
                    {
                        "name": "Zenka Loan App Kenya",
                        "package_name": "com.zenkafinance.microloans",
                        "developer": {"name": "Zenka Digital Limited"},
                        "url": "https://play.google.com/store/apps/details?id=com.zenkafinance.microloans",
                    },
                ]
            }
        ]
    }

    items = parse_talordata_search_items(
        payload,
        term="loan",
        observed_at=datetime(2026, 8, 19, tzinfo=UTC),
    )
    assert [item.package_name for item in items] == [
        "com.branch_international.branch.branch_demo_android",
        "com.zenkafinance.microloans",
    ]
    assert items[0].developer_name == "Branch International Financial Services Limited"
    assert items[0].source_provider == "talordata-google-play-search-v1"
    assert "token" not in items[0].source_url.casefold()
    assert "api_key" not in items[0].source_url.casefold()
