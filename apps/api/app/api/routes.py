from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.local_actions import require_local_action
from app.core.config import get_settings
from app.db.session import get_session
from app.schemas.regulatory import ReconciliationFinding
from app.schemas.rights import RightsRequestCreate, RightsRequestPreview
from app.services.dashboard import build_dashboard_summary
from app.services.snapshot_store import SnapshotStore
from app.services.source_sync import sync_source
from app.services.sources import find_source, load_manifest
from app.services.rights_templates import TemplateContext, render_request

router = APIRouter(prefix="/api/v1")


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


@router.get("/dashboard/summary")
def dashboard_summary(session: Session = Depends(get_session)) -> dict[str, object]:
    return build_dashboard_summary(session)


@router.post("/sources/{source_id}/sync", dependencies=[Depends(require_local_action)])
def sync_regulatory_source(
    source_id: str,
    session: Session = Depends(get_session),
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
    except Exception as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"source synchronization failed: {exc}",
        ) from exc

    return {
        "source_id": result.source_id,
        "snapshot_id": result.snapshot_id,
        "sha256": result.sha256,
        "record_count": result.record_count,
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
