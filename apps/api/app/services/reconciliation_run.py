from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import SourceObservation, SourceSnapshot
from app.db.repositories import ReconciliationRepository
from app.services.cbk_dcp import DcpDirectoryRecord
from app.services.odpc_registry import OdpcHandlerRecord
from app.services.regulatory_reconciliation import reconcile_cbk_odpc


class ReconciliationPrerequisiteError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReconciliationRunResult:
    cbk_snapshot_id: str
    odpc_snapshot_id: str
    finding_count: int


def _latest_snapshot(session: Session, source_id: str) -> SourceSnapshot | None:
    return session.scalar(
        select(SourceSnapshot)
        .where(SourceSnapshot.source_id == source_id)
        .order_by(SourceSnapshot.retrieved_at.desc(), SourceSnapshot.id.desc())
        .limit(1)
    )


def _observations(session: Session, snapshot_id: str) -> list[SourceObservation]:
    statement = (
        select(SourceObservation)
        .where(SourceObservation.snapshot_id == snapshot_id)
        .order_by(SourceObservation.external_id, SourceObservation.id)
    )
    return list(session.scalars(statement))


def _cbk_record(observation: SourceObservation) -> DcpDirectoryRecord:
    payload = json.loads(observation.payload_json)
    return DcpDirectoryRecord(
        sequence=int(payload["sequence"]),
        legal_name=str(payload["legal_name"]),
        trading_name=payload.get("trading_name"),
        website=payload.get("website"),
        emails=tuple(payload.get("emails") or ()),
        phones=tuple(payload.get("phones") or ()),
        postal_address=payload.get("postal_address"),
        physical_address=payload.get("physical_address"),
        licensed_date=payload.get("licensed_date"),
    )


def _odpc_record(observation: SourceObservation) -> OdpcHandlerRecord:
    payload = json.loads(observation.payload_json)
    return OdpcHandlerRecord(
        sequence=payload.get("sequence"),
        name=str(payload["name"]),
        handler_type=str(payload["handler_type"]),
        registration_number=str(payload["registration_number"]),
        county=payload.get("county"),
        country=payload.get("country"),
        status=str(payload["status"]),
        status_as_at=payload.get("status_as_at"),
    )


def run_cbk_odpc_reconciliation(session: Session) -> ReconciliationRunResult:
    cbk_snapshot = _latest_snapshot(session, "cbk_dcp")
    odpc_snapshot = _latest_snapshot(session, "odpc_registered")
    if cbk_snapshot is None or odpc_snapshot is None:
        raise ReconciliationPrerequisiteError(
            "latest CBK DCP and ODPC registered-handler snapshots are both required"
        )

    cbk_observations = _observations(session, cbk_snapshot.id)
    odpc_observations = _observations(session, odpc_snapshot.id)
    if not cbk_observations or not odpc_observations:
        raise ReconciliationPrerequisiteError(
            "latest CBK DCP and ODPC snapshots must contain parsed observations"
        )

    cbk_records = [_cbk_record(item) for item in cbk_observations]
    odpc_records = [_odpc_record(item) for item in odpc_observations]
    findings = reconcile_cbk_odpc(cbk_records, odpc_records)

    cbk_by_sequence = {int(item.external_id or "0"): item for item in cbk_observations}
    odpc_by_registration: dict[str, SourceObservation] = {}
    for item in odpc_observations:
        payload = json.loads(item.payload_json)
        registration = str(payload["registration_number"])
        odpc_by_registration.setdefault(registration, item)

    repository = ReconciliationRepository(session)
    for finding in findings:
        left = cbk_by_sequence[finding.cbk_sequence]
        right = (
            odpc_by_registration.get(finding.odpc_registration_number)
            if finding.odpc_registration_number
            else None
        )
        repository.record(
            left_source_key=f"{cbk_snapshot.id}:{left.external_id}",
            right_source_key=(
                f"{odpc_snapshot.id}:{right.external_id}" if right is not None else None
            ),
            finding_type=finding.finding_type,
            confidence=finding.confidence,
            summary=finding.summary,
        )
    session.flush()

    return ReconciliationRunResult(
        cbk_snapshot_id=cbk_snapshot.id,
        odpc_snapshot_id=odpc_snapshot.id,
        finding_count=len(findings),
    )
