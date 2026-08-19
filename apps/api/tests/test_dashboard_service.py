from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import ReconciliationFinding, RightsRequest, SourceObservation, SourceSnapshot
from app.services.dashboard import build_dashboard_summary


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_dashboard_summary_is_derived_from_latest_persisted_snapshots() -> None:
    now = datetime.now(UTC)
    with _session() as session:
        old_cbk = SourceSnapshot(
            source_id="cbk_dcp",
            source_url="https://www.centralbank.go.ke/old.pdf",
            sha256="a" * 64,
            media_type="application/pdf",
            retrieved_at=now - timedelta(days=1),
            storage_path="old.pdf",
        )
        new_cbk = SourceSnapshot(
            source_id="cbk_dcp",
            source_url="https://www.centralbank.go.ke/current.pdf",
            sha256="b" * 64,
            media_type="application/pdf",
            retrieved_at=now,
            storage_path="current.pdf",
        )
        odpc = SourceSnapshot(
            source_id="odpc_registered",
            source_url="https://www.odpc.go.ke/registered-data-handlers/",
            sha256="c" * 64,
            media_type="text/html",
            retrieved_at=now,
            storage_path="odpc.html",
        )
        session.add_all([old_cbk, new_cbk, odpc])
        session.flush()
        session.add(SourceObservation(snapshot_id=old_cbk.id, regulator="CBK", external_id="1", status="licensed", payload_json="{}"))
        session.add_all([
            SourceObservation(snapshot_id=new_cbk.id, regulator="CBK", external_id="1", status="licensed", payload_json="{}"),
            SourceObservation(snapshot_id=new_cbk.id, regulator="CBK", external_id="2", status="licensed", payload_json="{}"),
            SourceObservation(snapshot_id=odpc.id, regulator="ODPC", external_id="INST-1:data_controller", status="Active", payload_json="{}"),
        ])
        session.add(RightsRequest(right_type="access", state="draft"))
        session.add(
            ReconciliationFinding(
                finding_key="d" * 64,
                left_source_key="cbk:1",
                finding_type="candidate_match",
                confidence=0.96,
                summary="Manual review required",
                review_state="pending",
            )
        )
        session.commit()

        summary = build_dashboard_summary(session)
        assert summary["counts"]["cbk_dcp_reference_count"] == 2
        assert summary["counts"]["odpc_synced"] is True
        assert summary["counts"]["open_requests"] == 1
        assert summary["counts"]["manual_review"] == 1
        assert summary["sources"]["cbk_dcp"]["sha256"] == "b" * 64
        assert summary["sources"]["cbk_dcp"]["record_count"] == 2


def test_empty_database_reports_unsynced_without_fake_counts() -> None:
    with _session() as session:
        summary = build_dashboard_summary(session)
        assert summary["counts"]["cbk_dcp_reference_count"] == 0
        assert summary["counts"]["odpc_synced"] is False
        assert summary["sources"] == {}
