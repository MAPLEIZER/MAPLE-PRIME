from pathlib import Path

from app.services.legal_library import load_legal_library, search_legal_library


def test_legal_library_has_authoritative_core_sources_and_searchable_sections() -> None:
    root = Path(__file__).resolve().parents[3]
    entries = load_legal_library(root / "docs" / "legal" / "index.json")
    ids = {entry.id for entry in entries}
    assert {
        "constitution-article-31",
        "data-protection-act",
        "data-protection-general-regulations",
        "data-protection-registration-regulations",
        "data-protection-complaints-enforcement",
        "computer-misuse-cybercrimes-act",
        "digital-credit-providers-regulations",
        "credit-reference-bureau-regulations",
        "access-to-information-act",
        "consumer-protection-act",
        "kenya-information-communications-act",
    } <= ids
    assert all(entry.source_url.startswith("https://") for entry in entries)
    assert all(entry.official_source for entry in entries)


def test_search_finds_relevant_sections_without_making_legal_conclusions() -> None:
    root = Path(__file__).resolve().parents[3]
    entries = load_legal_library(root / "docs" / "legal" / "index.json")
    results = search_legal_library(entries, "loan app contacts debt collection privacy", limit=5)
    assert results
    assert any(result.id == "digital-credit-providers-regulations" for result in results)
    assert any("possible" in result.caution.lower() or "not legal advice" in result.caution.lower() for result in results)
