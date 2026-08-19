from datetime import UTC, datetime

from app.services.play_store_discovery import (
    parse_serpapi_product,
    parse_serpapi_search_package_ids,
    selected_discovery_provider,
)


def test_serpapi_search_parser_collects_package_ids_from_google_play_sections() -> None:
    payload = {
        "app_highlight": {"product_id": "ke.co.alpha.cash"},
        "organic_results": [
            {
                "title": "Apps",
                "items": [
                    {"product_id": "ke.co.beta.loan"},
                    {"product_id": "ke.co.alpha.cash"},
                ],
            }
        ],
    }
    assert parse_serpapi_search_package_ids(payload) == [
        "ke.co.alpha.cash",
        "ke.co.beta.loan",
    ]


def test_serpapi_product_parser_maps_developer_contact_into_normalized_app_evidence() -> None:
    payload = {
        "product_info": {
            "title": "Alpha Cash",
            "authors": [{"name": "Alpha Credit Limited"}],
            "downloads": "100K+",
        },
        "developer_contact": {
            "website": "https://alpha.co.ke",
            "support_email": "support@alpha.co.ke",
            "privacy_policy": "https://alpha.co.ke/privacy",
            "name": "Alpha Credit Limited",
        },
    }
    item = parse_serpapi_product(
        "ke.co.alpha.cash",
        payload,
        observed_at=datetime(2026, 8, 19, tzinfo=UTC),
    )
    assert item.package_name == "ke.co.alpha.cash"
    assert item.app_name == "Alpha Cash"
    assert item.developer_name == "Alpha Credit Limited"
    assert item.support_email == "support@alpha.co.ke"
    assert item.developer_website == "https://alpha.co.ke"
    assert item.privacy_policy_url == "https://alpha.co.ke/privacy"
    assert item.source_provider == "serpapi-google-play-v1"
    assert "api_key" not in item.source_url


def test_auto_provider_prefers_serpapi_when_key_is_configured_and_keeps_public_fallback() -> None:
    assert selected_discovery_provider("auto", serpapi_api_key="secret") == "serpapi"
    assert selected_discovery_provider("auto", serpapi_api_key=None) == "public_html"
    assert selected_discovery_provider("serpapi", serpapi_api_key="secret") == "serpapi"
