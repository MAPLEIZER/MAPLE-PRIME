from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LegalEntry:
    id: str
    title: str
    citation: str
    summary: str
    topics: tuple[str, ...]
    provisions: tuple[str, ...]
    source_url: str
    source_date: str
    official_source: bool
    chapter: str
    caution: str

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "citation": self.citation,
            "summary": self.summary,
            "topics": list(self.topics),
            "provisions": list(self.provisions),
            "source_url": self.source_url,
            "source_date": self.source_date,
            "official_source": self.official_source,
            "chapter": self.chapter,
            "caution": self.caution,
        }


def load_legal_library(path: Path) -> list[LegalEntry]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("legal library index must be a list")
    entries: list[LegalEntry] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("legal library item must be an object")
        entry = LegalEntry(
            id=str(item["id"]),
            title=str(item["title"]),
            citation=str(item["citation"]),
            summary=str(item["summary"]),
            topics=tuple(str(value) for value in item.get("topics", [])),
            provisions=tuple(str(value) for value in item.get("provisions", [])),
            source_url=str(item["source_url"]),
            source_date=str(item["source_date"]),
            official_source=bool(item.get("official_source", False)),
            chapter=str(item["chapter"]),
            caution=str(item["caution"]),
        )
        if not entry.official_source or not entry.source_url.startswith("https://"):
            raise ValueError("legal library entries must use authoritative HTTPS sources")
        entries.append(entry)
    return entries


def search_legal_library(entries: list[LegalEntry], query: str, *, limit: int = 10) -> list[LegalEntry]:
    terms = [term for term in re.findall(r"[a-z0-9]+", query.lower()) if len(term) > 1]
    if not terms:
        return entries[: max(1, min(limit, 50))]

    scored: list[tuple[int, LegalEntry]] = []
    for entry in entries:
        title = entry.title.lower()
        topics = " ".join(entry.topics).lower()
        body = " ".join([entry.summary, *entry.provisions, entry.caution]).lower()
        score = 0
        for term in terms:
            if term in title:
                score += 5
            if term in topics:
                score += 4
            if term in body:
                score += 2
        if score:
            scored.append((score, entry))
    scored.sort(key=lambda pair: (-pair[0], pair[1].title))
    return [entry for _, entry in scored[: max(1, min(limit, 50))]]
