from __future__ import annotations

import json
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from app.services.fetcher import fetch_source
from app.services.sources import SourceDefinition

_RELEVANT_TERMS = frozenset(
    {
        "artificial intelligence",
        " ai ",
        "data protection",
        "data privacy",
        "data governance",
        "cybersecurity",
        "cyber security",
        "cybercrime",
        "digital credit",
        "digital lender",
        "emerging technologies",
        "information and communications",
        "kica",
        "privacy",
    }
)


@dataclass(frozen=True)
class CivicDiscoverySource:
    id: str
    agency: str
    url: str


@dataclass(frozen=True)
class CivicCandidate:
    source_id: str
    agency: str
    title: str
    url: str
    requires_review: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "agency": self.agency,
            "title": self.title,
            "url": self.url,
            "requires_review": self.requires_review,
        }


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._href: str | None = None
        self._text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._href = href.strip()
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            title = " ".join(" ".join(self._text).split())
            if title:
                self.links.append((self._href, title))
            self._href = None
            self._text = []


def load_discovery_sources(path: Path) -> list[CivicDiscoverySource]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("civic discovery sources must be a list")
    sources = [
        CivicDiscoverySource(id=str(item["id"]), agency=str(item["agency"]), url=str(item["url"]))
        for item in payload
        if isinstance(item, dict)
    ]
    if not sources or any(urlsplit(source.url).scheme != "https" for source in sources):
        raise ValueError("civic discovery sources must use HTTPS")
    return sources


def _is_relevant(title: str) -> bool:
    padded = f" {title.lower()} "
    return any(term in padded for term in _RELEVANT_TERMS)


def discover_candidates(source: CivicDiscoverySource, html: bytes) -> list[CivicCandidate]:
    parser = _LinkParser()
    parser.feed(html.decode("utf-8", errors="replace"))
    source_host = (urlsplit(source.url).hostname or "").lower()
    seen: set[str] = set()
    results: list[CivicCandidate] = []
    for href, title in parser.links:
        if not _is_relevant(title):
            continue
        absolute = urljoin(source.url, href)
        parsed = urlsplit(absolute)
        if parsed.scheme != "https" or (parsed.hostname or "").lower() != source_host:
            continue
        normalized = parsed._replace(fragment="").geturl()
        if normalized in seen:
            continue
        seen.add(normalized)
        results.append(
            CivicCandidate(
                source_id=source.id,
                agency=source.agency,
                title=title[:400],
                url=normalized,
            )
        )
    return results[:100]


def scan_official_consultation_sources(sources: list[CivicDiscoverySource]) -> list[CivicCandidate]:
    candidates: list[CivicCandidate] = []
    seen: set[str] = set()
    for source in sources:
        definition = SourceDefinition(
            id=source.id,
            regulator=source.agency,
            url=source.url,
            parser="civic_html_links_v1",
            update_policy="manual",
            category="public_participation",
            media_type="text/html",
        )
        fetched = fetch_source(definition, max_bytes=5 * 1024 * 1024)
        if fetched.media_type not in {"text/html", "application/xhtml+xml"}:
            continue
        for candidate in discover_candidates(source, fetched.body):
            if candidate.url not in seen:
                seen.add(candidate.url)
                candidates.append(candidate)
    return candidates[:250]
