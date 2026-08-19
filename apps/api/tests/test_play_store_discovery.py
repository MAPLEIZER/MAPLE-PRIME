from datetime import UTC, datetime

from app.services.play_store_discovery import (
    build_play_search_url,
    parse_play_detail_html,
    parse_play_search_package_ids,
)


def test_play_search_parser_deduplicates_public_package_ids() -> None:
    html = """
    <a href="/store/apps/details?id=ke.co.alpha.loan">Alpha</a>
    <a href="/store/apps/details?id=ke.co.alpha.loan&hl=en">Again</a>
    <a href="/store/apps/details?id=com.beta.cash">Beta</a>
    """
    assert parse_play_search_package_ids(html) == ["ke.co.alpha.loan", "com.beta.cash"]


def test_play_detail_parser_normalizes_public_metadata_for_registry_ingestion() -> None:
    html = """
    <html><head>
      <script type="application/ld+json">
      {"@type":"SoftwareApplication","name":"Alpha Cash","author":{"name":"Alpha Credit Limited"},"applicationCategory":"FinanceApplication","numDownloads":"100,000+"}
      </script>
    </head><body>
      <a href="mailto:support@alpha.co.ke">Email developer</a>
      <a href="https://alpha.co.ke/privacy-policy">Privacy Policy</a>
    </body></html>
    """
    item = parse_play_detail_html(
        "ke.co.alpha.loan",
        html,
        observed_at=datetime(2026, 8, 19, tzinfo=UTC),
    )
    assert item.package_name == "ke.co.alpha.loan"
    assert item.app_name == "Alpha Cash"
    assert item.developer_name == "Alpha Credit Limited"
    assert item.support_email == "support@alpha.co.ke"
    assert item.privacy_policy_url == "https://alpha.co.ke/privacy-policy"
    assert item.source_provider == "kdr-google-play-public-html-v1"
    assert item.source_url.startswith("https://play.google.com/")


def test_play_search_url_is_scoped_to_kenya_and_google_play() -> None:
    url = build_play_search_url("Alpha Credit Limited")
    assert url.startswith("https://play.google.com/store/search?")
    assert "gl=KE" in url
    assert "c=apps" in url
