from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ReconciliationFinding, RightsRequest, SourceObservation, SourceSnapshot

TERMINAL_REQUEST_STATES = frozenset({"completed", "cancelled", "closed"})


def _latest_snapshots(session: Session) -> dict[str, SourceSnapshot]:
    snapshots = session.scalars(
        select(SourceSnapshot).order_by(SourceSnapshot.retrieved_at.desc())
    ).all()
    latest: dict[str, SourceSnapshot] = {}
    for snapshot in snapshots:
        latest.setdefault(snapshot.source_id, snapshot)
    return latest


def _observation_count(session: Session, snapshot_id: str) -> int:
    return int(
        session.scalar(
            select(func.count(SourceObservation.id)).where(
                SourceObservation.snapshot_id == snapshot_id
            )
        )
        or 0
    )


def build_dashboard_summary(session: Session) -> dict[str, object]:
    latest = _latest_snapshots(session)
    sources = {
        source_id: {
            "snapshot_id": snapshot.id,
            "sha256": snapshot.sha256,
            "retrieved_at": snapshot.retrieved_at.isoformat(),
            "record_count": _observation_count(session, snapshot.id),
        }
        for source_id, snapshot in latest.items()
    }

    cbk = sources.get("cbk_dcp")
    open_requests = int(
        session.scalar(
            select(func.count(RightsRequest.id)).where(
                RightsRequest.state.not_in(TERMINAL_REQUEST_STATES)
            )
        )
        or 0
    )
    manual_review = int(
        session.scalar(
            select(func.count(ReconciliationFinding.id)).where(
                ReconciliationFinding.review_state == "pending"
            )
        )
        or 0
    )

    return {
        "project_status": "alpha",
        "regulatory_sources": ["CBK", "ODPC", "CRB", "Kenya Law"],
        "counts": {
            "cbk_dcp_reference_count": int(cbk["record_count"]) if cbk else 0,
            "odpc_synced": "odpc_registered" in sources,
            "open_requests": open_requests,
            "manual_review": manual_review,
        },
        "sources": sources,
        "disclaimer": "Reference counts are source-snapshot facts, not compliance scores.",
    }
