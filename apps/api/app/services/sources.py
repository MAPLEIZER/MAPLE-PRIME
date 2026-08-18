from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, Field


class SourceDefinition(BaseModel):
    id: str
    regulator: str
    url: str
    parser: str
    update_policy: str = "manual"
    category: str | None = None
    media_type: str | None = None
    expected_record_count: int | None = Field(default=None, ge=1)
    published_at: str | None = None


class SourceManifest(BaseModel):
    sources: list[SourceDefinition] = Field(default_factory=list)


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    sources = raw.get("sources", [])
    if isinstance(sources, dict):
        normalized = []
        for source_id, item in sources.items():
            row = dict(item or {})
            row.setdefault("id", source_id)
            row.setdefault(
                "regulator",
                row.pop("authority", source_id.split("_", 1)[0].upper()),
            )
            row.setdefault("update_policy", row.pop("expected_frequency", "manual"))
            if "media_type" not in row and "type" in row:
                row["media_type"] = row.pop("type")
            row.pop("trust", None)
            normalized.append(row)
        return {"sources": normalized}
    return raw


def load_manifest(path: Path) -> SourceManifest:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    manifest = SourceManifest.model_validate(_normalize(raw))
    for source in manifest.sources:
        parsed = urlsplit(source.url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError(f"source {source.id} must use an absolute HTTPS URL")
    return manifest


def find_source(manifest: SourceManifest, source_id: str) -> SourceDefinition:
    for source in manifest.sources:
        if source.id == source_id:
            return source
    raise KeyError(source_id)
