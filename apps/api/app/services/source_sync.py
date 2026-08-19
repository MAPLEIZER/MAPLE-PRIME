from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.db.repositories import SourceRepository
from app.services.cbk_import import parse_cbk_pdf
from app.services.fetcher import SourceFetchError, fetch_source
from app.services.odpc_registry import OdpcRegistryAccessRestricted, parse_registered_handlers_html
from app.services.snapshot_store import SnapshotStore
from app.services.sources import SourceDefinition


class UnsupportedSourceParser(ValueError):
    pass


@dataclass(frozen=True)
class SyncResult:
    source_id: str
    snapshot_id: str
    sha256: str
    record_count: int
    content_path: Path


def _observation(record: Any, source: SourceDefinition) -> tuple[str | None, str, str]:
    payload = json.dumps(asdict(record), sort_keys=True, default=str, separators=(",", ":"))
    if source.parser == "odpc_handlers_v1":
        role = re.sub(r"[^a-z0-9]+", "_", record.handler_type.lower()).strip("_")
        return f"{record.registration_number}:{role}", record.status, payload
    if source.parser == "cbk_dcp_pdf_v1":
        return str(record.sequence), "licensed", payload
    raise UnsupportedSourceParser(source.parser)


def _parse(source: SourceDefinition, body: bytes) -> list[Any]:
    if source.parser == "odpc_handlers_v1":
        try:
            html = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("ODPC source was not UTF-8 HTML") from exc
        try:
            return list(parse_registered_handlers_html(html))
        except OdpcRegistryAccessRestricted as exc:
            raise SourceFetchError(
                "ODPC returned an access/challenge page instead of registry data",
                code="source_access_restricted",
            ) from exc
    if source.parser == "cbk_dcp_pdf_v1":
        return list(parse_cbk_pdf(body, source))
    raise UnsupportedSourceParser(source.parser)


def sync_source(
    source: SourceDefinition,
    *,
    store: SnapshotStore,
    session: Session,
    transport: httpx.BaseTransport | None = None,
    retrieved_at: datetime | None = None,
) -> SyncResult:
    fetched = fetch_source(source, transport=transport)
    observed_at = retrieved_at or datetime.now(UTC)
    stored = store.put(
        source_id=source.id,
        body=fetched.body,
        media_type=fetched.media_type,
        retrieved_at=observed_at.isoformat(),
    )
    records = _parse(source, fetched.body)

    repository = SourceRepository(session)
    snapshot = repository.record_snapshot(
        source_id=source.id,
        source_url=fetched.url,
        sha256=stored.sha256,
        media_type=fetched.media_type,
        retrieved_at=observed_at,
        storage_path=str(stored.content_path),
    )
    if not repository.has_observations(snapshot.id):
        for record in records:
            external_id, status, payload = _observation(record, source)
            repository.add_observation(
                snapshot_id=snapshot.id,
                regulator=source.regulator,
                external_id=external_id,
                status=status,
                payload_json=payload,
            )
        session.flush()

    return SyncResult(
        source_id=source.id,
        snapshot_id=snapshot.id,
        sha256=stored.sha256,
        record_count=len(records),
        content_path=stored.content_path,
    )
