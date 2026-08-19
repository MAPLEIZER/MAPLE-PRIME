from datetime import UTC, datetime

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base import Base
from app.db.repositories import AppRegistryRepository
from app.schemas.apps import PlayAppImportItem
from app.services.play_research import (
    PlayResearchOptions,
    _next_serpapi_page_token,
    _serpapi_chart_options,
    _serpapi_section_page_tokens,
    normalize_research_queries,
    run_play_research,
)


def test_research_queries_are_normalized_deduplicated_and_bounded() -> None:
    queries = normalize_research_queries([" loan ", "LOAN", "mkopo", "salary   advance", ""])
    assert queries == ("loan", "mkopo", "salary advance")


def test_serpapi_pagination_and_category_breadth_tokens_are_parsed() -> None:
    payload = {
        "serpapi_pagination": {"next_page_token": "next-123"},
        "chart_options": [
            {"text": "Top free", "value": "topselling_free"},
            {"text": "Top grossing", "value": "topgrossing"},
        ],
        "organic_results": [
            {
                "title": "Finance apps",
                "serpapi_section_pagination": {"section_page_token": "section-a"},
                "items": [],
            },
            {
                "title": "Money management",
                "serpapi_section_pagination": {"section_page_token": "section-b"},
                "items": [],
            },
        ],
    }
    assert _next_serpapi_page_token(payload) == "next-123"
    assert _serpapi_section_page_tokens(payload) == [
        ("Finance apps", "section-a"),
        ("Money management", "section-b"),
    ]
    assert _serpapi_chart_options(payload) == [
        ("Top free", "topselling_free"),
        ("Top grossing", "topgrossing"),
    ]
    assert _next_serpapi_page_token({}) is None


def test_category_research_paginates_skips_existing_packages_and_flags_reused_emails() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        if params.get("engine") == "google_play_product":
            package = params["product_id"]
            email = "shared@example.co.ke" if package == "ke.co.new.alpha" else "fresh@example.co.ke"
            return httpx.Response(
                200,
                json={
                    "product_info": {
                        "title": "Alpha Loan" if package.endswith("alpha") else "Beta Credit",
                        "authors": [{"name": "Alpha Finance Ltd" if package.endswith("alpha") else "Beta Finance Ltd"}],
                        "downloads": "10,000+",
                    },
                    "developer_contact": {
                        "support_email": email,
                        "website": "https://example.co.ke",
                    },
                },
            )
        if params.get("next_page_token") == "page-two":
            return httpx.Response(
                200,
                json={
                    "organic_results": [{
                        "items": [
                            {"product_id": "ke.co.new.alpha", "title": "Alpha Loan", "author": "Alpha Finance Ltd"},
                            {"product_id": "ke.co.new.beta", "title": "Beta Credit", "author": "Beta Finance Ltd"},
                        ]
                    }],
                    "request_params": {"engine": "google_play", "store": "apps", "apps_category": "FINANCE", "gl": "ke", "hl": "en"},
                },
            )
        return httpx.Response(
            200,
            json={
                "organic_results": [{
                    "items": [
                        {"product_id": "ke.co.existing.loan", "title": "Existing Loan", "author": "Existing Finance Ltd"},
                        {"product_id": "ke.co.new.alpha", "title": "Alpha Loan", "author": "Alpha Finance Ltd"},
                    ]
                }],
                "serpapi_pagination": {"next_page_token": "page-two"},
                "request_params": {"engine": "google_play", "store": "apps", "apps_category": "FINANCE", "gl": "ke", "hl": "en"},
            },
        )

    with Session(engine) as session:
        repository = AppRegistryRepository(session)
        repository.ingest_play(
            PlayAppImportItem(
                package_name="ke.co.existing.loan",
                app_name="Existing Loan",
                developer_name="Existing Finance Ltd",
                support_email="shared@example.co.ke",
                store_url="https://play.google.com/store/apps/details?id=ke.co.existing.loan",
                source_provider="fixture",
                source_url="https://play.google.com/store/apps/details?id=ke.co.existing.loan",
                observed_at=datetime(2026, 8, 19, tzinfo=UTC),
            )
        )
        client = httpx.Client(transport=httpx.MockTransport(handler))
        result = run_play_research(
            session,
            options=PlayResearchOptions(
                provider="serpapi",
                mode="category",
                max_pages=2,
                max_apps=20,
                enrich_limit=2,
                skip_existing=True,
            ),
            settings=Settings(
                play_discovery_provider="serpapi",
                serpapi_api_key="test-key",
            ),
            client=client,
        )

        assert result["pages_fetched"] == 2
        assert result["unique_apps_discovered"] == 3
        assert result["new_apps"] == 2
        assert result["existing_apps"] == 1
        assert result["skipped_existing_apps"] == 1
        assert result["apps_ingested"] == 2
        assert result["duplicate_packages_skipped"] == 1
        assert result["emails_found"] == 3
        assert result["existing_email_hits"] == 2
        assert result["new_unique_emails"] == 1
        rows = {row["package_name"]: row for row in result["results"]}
        assert rows["ke.co.existing.loan"]["database_status"] == "existing"
        assert rows["ke.co.new.alpha"]["email_status"] == "existing"
        assert rows["ke.co.new.beta"]["email_status"] == "new"
