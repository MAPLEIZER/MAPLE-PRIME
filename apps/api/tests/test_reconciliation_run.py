import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import SourceObservation, SourceSnapshot
from app.db.repositories import ReconciliationRepository
from app.services.reconciliation_run import (
    ReconciliationPrerequisiteError,
    run_cbk_odpc_reconciliation,
)


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _snapshot(session: Session, source_id: str, sha: str, retrieved_at: datetime) -> SourceSnapshot:
    item = SourceSnapshot(
        source_id=source_id,
        source_url=f"https://example.invalid/{source_id}",
        sha256=sha,
        media_type="application/octet-stream",
        retrieved_at=retrieved_at,
        storage_path=f"/{sha}",
    )
    session.add(item)
    session.flush()
    return item


def test_reconciliation_auto_confirms_only_high_confidence_identity_matches() -> None:
    now = datetime.now(UTC)
    with _session() as session:
        old_cbk = _snapshot(session, "cbk_dcp", "a" * 64, now - timedelta(days=1))
        cbk = _snapshot(session, "cbk_dcp", "b" * 64, now)
        odpc = _snapshot(session, "odpc_registered", "c" * 64, now)

        session.add(
            SourceObservation(
                snapshot_id=old_cbk.id,
                regulator="CBK",
                external_id="1",
                status="licensed",
                payload_json=json.dumps({"sequence": 1, "legal_name": "Old Name Limited"}),
            )
        )
        session.add_all(
            [
                SourceObservation(
                    snapshot_id=cbk.id,
                    regulator="CBK",
                    external_id="1",
                    status="licensed",
                    payload_json=json.dumps({"sequence": 1, "legal_name": "Example Credit Limited"}),
                ),
                SourceObservation(
                    snapshot_id=cbk.id,
                    regulator="CBK",
                    external_id="2",
                    status="licensed",
                    payload_json=json.dumps({"sequence": 2, "legal_name": "Missing Finance Limited"}),
                ),
                SourceObservation(
                    snapshot_id=odpc.id,
                    regulator="ODPC",
                    external_id="INST-1:data_controller",
                    status="Active/Renewed",
                    payload_json=json.dumps(
                        {
                            "sequence": 1,
                            "name": "Example Credit Ltd",
                            "handler_type": "Data Controller",
                            "registration_number": "INST-1",
                            "county": "NAIROBI",
                            "country": "Kenya",
                            "status": "Active/Renewed",
                            "status_as_at": "7/9/2026",
                        }
                    ),
                ),
            ]
        )
        session.commit()

        result = run_cbk_odpc_reconciliation(session)
        session.commit()

        assert result.cbk_snapshot_id == cbk.id
        assert result.odpc_snapshot_id == odpc.id
        assert result.finding_count == 2
        findings = ReconciliationRepository(session).list(limit=10)
        matched = next(item for item in findings if item.finding_type == "candidate_match")
        missing = next(item for item in findings if item.finding_type == "not_located")
        assert matched.confidence >= 0.90
        assert matched.review_state == "confirmed"
        assert matched.reviewed_by == "system:auto_identity_threshold_v1"
        assert missing.review_state == "pending"
        assert all(item.left_source_key.startswith(f"{cbk.id}:") for item in findings)
        assert missing.right_source_key is None
        assert "not located" in missing.summary.lower()
        assert "non-compliance" in missing.summary.lower()


def test_reconciliation_refuses_to_run_without_both_latest_source_snapshots() -> None:
    with _session() as session:
        _snapshot(session, "cbk_dcp", "a" * 64, datetime.now(UTC))
        session.commit()
        with pytest.raises(ReconciliationPrerequisiteError):
            run_cbk_odpc_reconciliation(session)
