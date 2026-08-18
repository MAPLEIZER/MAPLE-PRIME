from app.services.civic_discovery import CivicDiscoverySource, discover_candidates


def test_discovery_extracts_relevant_official_links_and_ignores_unrelated_content() -> None:
    source = CivicDiscoverySource(
        id="ict-participation",
        agency="Ministry of ICT",
        url="https://ict.go.ke/call-public-partipation",
    )
    html = b"""
    <html><body>
      <a href="/ai-policy-comments">Call for comments: Draft Artificial Intelligence Policy 2026</a>
      <a href="https://ict.go.ke/data-governance">Public participation: National Data Governance Policy</a>
      <a href="/jobs">Internal Jobs Advertisement 2026</a>
    </body></html>
    """
    results = discover_candidates(source, html)
    assert [item.title for item in results] == [
        "Call for comments: Draft Artificial Intelligence Policy 2026",
        "Public participation: National Data Governance Policy",
    ]
    assert all(item.url.startswith("https://ict.go.ke/") for item in results)
    assert all(item.requires_review for item in results)


def test_discovery_rejects_cross_domain_links_and_deduplicates() -> None:
    source = CivicDiscoverySource(
        id="parliament",
        agency="Parliament",
        url="https://www.parliament.go.ke/public-participation",
    )
    html = b"""
      <a href="https://evil.example/privacy-bill">Privacy Bill public participation</a>
      <a href="/memorandum-data-protection">Invitation: Data Protection Bill memorandum</a>
      <a href="/memorandum-data-protection">Invitation: Data Protection Bill memorandum</a>
    """
    results = discover_candidates(source, html)
    assert len(results) == 1
    assert results[0].url == "https://www.parliament.go.ke/memorandum-data-protection"
