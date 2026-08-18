from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.local_actions import (
    require_local_action,
    require_reconcile_action,
    require_review_action,
)
from app.core.config import get_settings
from app.db.repositories import ReconciliationRepository
from app.db.session import get_engine, get_session
from app.schemas.regulatory import ReconciliationFinding, ReconciliationReviewInput
from app.schemas.rights import RightsRequestCreate, RightsRequestPreview
from app.selftest import run_internal_checks
from app.services.cbk_import import SourceParseError
from app.services.dashboard import build_dashboard_summary
from app.services.fetcher import SourceFetchError
from app.services.reconciliation_run import (
    ReconciliationPrerequisiteError,
    run_cbk_odpc_reconciliation,
)
from app.services.rights_templates import TemplateContext, render_request
from app.services.snapshot_store import SnapshotStore
from app.services.source_sync import UnsupportedSourceParser, sync_source
from app.services.sources import find_source, load_manifest

router = APIRouter(prefix="/api/v1")
DbSession = Annotated[Session, Depends(get_session)]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}


@router.get("/system/status")
def system_status() -> dict[str, object]:
    return {
        "release_stage": "alpha",
        "local_first": True,
        "telemetry": False,
        "sensitive_logging": False,
        "mobile_shared_data": "mapping_metadata_only",
    }


@router.get("/system/self-test")
def system_self_test() -> dict[str, object]:
    settings = get_settings()
    return run_internal_checks(
        engine=get_engine(),
        manifest_path=Path(settings.source_manifest_path),
        snapshot_dir=Path(settings.snapshot_dir),
    )


@router.get("/dashboard/summary")
def dashboard_summary(session: DbSession) -> dict[str, object]:
    return build_dashboard_summary(session)


@router.post("/sources/{source_id}/sync", dependencies=[Depends(require_local_action)])
def sync_regulatory_source(
    source_id: str,
    session: DbSession,
) -> dict[str, object]:
    settings = get_settings()
    try:
        manifest = load_manifest(Path(settings.source_manifest_path))
        source = find_source(manifest, source_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="source id is not present in the approved manifest",
        ) from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="approved source manifest is unavailable or invalid",
        ) from exc

    try:
        result = sync_source(
            source,
            store=SnapshotStore(Path(settings.snapshot_dir)),
            session=session,
        )
        session.commit()
    except (SourceFetchError, SourceParseError, UnsupportedSourceParser, OSError, ValueError) as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="approved source synchronization failed",
        ) from exc
    except Exception:
        session.rollback()
        raise

    return {
        "source_id": result.source_id,
        "snapshot_id": result.snapshot_id,
        "sha256": result.sha256,
        "record_count": result.record_count,
    }


@router.post(
    "/reconciliation/cbk-odpc/run",
    dependencies=[Depends(require_reconcile_action)],
)
def run_reconciliation(session: DbSession) -> dict[str, object]:
    try:
        result = run_cbk_odpc_reconciliation(session)
        session.commit()
    except ReconciliationPrerequisiteError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CBK and ODPC snapshots must both be synced before reconciliation",
        ) from exc
    except Exception:
        session.rollback()
        raise
    return {
        "cbk_snapshot_id": result.cbk_snapshot_id,
        "odpc_snapshot_id": result.odpc_snapshot_id,
        "finding_count": result.finding_count,
    }


@router.get("/reconciliation/findings")
def reconciliation_findings(session: DbSession, limit: int = 500) -> list[dict[str, object]]:
    safe_limit = max(1, min(limit, 1000))
    return [
        {
            "id": item.id,
            "finding_type": item.finding_type,
            "confidence": item.confidence,
            "summary": item.summary,
            "review_state": item.review_state,
            "left_source_key": item.left_source_key,
            "right_source_key": item.right_source_key,
            "reviewed_by": item.reviewed_by,
            "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
        }
        for item in ReconciliationRepository(session).list(limit=safe_limit)
    ]


@router.post(
    "/reconciliation/findings/{finding_id}/review",
    dependencies=[Depends(require_review_action)],
)
def review_reconciliation_finding(
    finding_id: str,
    payload: ReconciliationReviewInput,
    session: DbSession,
) -> dict[str, object]:
    repository = ReconciliationRepository(session)
    try:
        finding = repository.resolve(
            finding_id,
            decision=payload.decision,
            reviewer="local_user",
            institution_id=payload.institution_id,
        )
        session.commit()
    except KeyError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="reconciliation finding was not found",
        ) from exc
    except Exception:
        session.rollback()
        raise
    return {
        "id": finding.id,
        "review_state": finding.review_state,
        "reviewed_by": finding.reviewed_by,
        "reviewed_at": finding.reviewed_at.isoformat() if finding.reviewed_at else None,
        "resolved_institution_id": finding.resolved_institution_id,
    }


@router.get("/reconciliation/sample", response_model=list[ReconciliationFinding])
def sample_findings() -> list[ReconciliationFinding]:
    return [
        ReconciliationFinding(
            code="SOURCE_SYNC_PENDING",
            severity="review",
            entity_id=None,
            title="ODPC full reconciliation not yet synced",
            detail=(
                "No conclusion should be drawn until the production ODPC importer has captured and "
                "versioned the current public registry snapshot."
            ),
            source_snapshot_ids=[],
            confidence=1.0,
            requires_manual_review=True,
        )
    ]


@router.post("/rights/preview", response_model=RightsRequestPreview)
def preview_request(payload: RightsRequestCreate) -> RightsRequestPreview:
    subject, body, warnings = render_request(
        payload.right_type,
        TemplateContext(
            full_name="<YOUR NAME>",
            institution_name="<TARGET INSTITUTION>",
        ),
    )
    return RightsRequestPreview(subject=subject, body=body, warnings=warnings)
