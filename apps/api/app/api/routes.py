from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.regulatory import ReconciliationFinding
from app.schemas.rights import RightsRequestCreate, RightsRequestPreview
from app.services.dashboard import build_dashboard_summary
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
