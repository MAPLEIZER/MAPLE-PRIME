from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.local_actions import (
    require_local_action,
    require_reconcile_action,
    require_review_action,
)
from app.api.mobile_auth import require_mobile_bearer
from app.core.config import get_settings
from app.db.models import SourceObservation
from app.db.repositories import MobileTelemetryRepository, ReconciliationRepository
from app.db.session import get_engine, get_session
from app.schemas.mobile import MobileLabelUpdate, MobileTelemetryBatch, MobileTelemetryEvent
from app.schemas.regulatory import ReconciliationFinding, ReconciliationReviewInput
from app.schemas.rights import RightsRequestCreate, RightsRequestPreview
from app.selftest import run_internal_checks
from app.services.cbk_import import SourceParseError
from app.services.dashboard import build_dashboard_summary
from app.services.fetcher import SourceFetchError
from app.services.message_classifier import MODEL_VERSION, classify_features
from app.services.reconcile import normalize_legal_name
from app.services.reconciliation_run import (
    ReconciliationPrerequisiteError,
    run_cbk_odpc_reconciliation,
)
from app.services.rights_templates import TemplateContext, render_request
from app.services.snapshot_store import SnapshotStore
from app.services.source_sync import UnsupportedSourceParser, sync_source
from app.services.sources import find_source, load_manifest
from app.services.sync_diagnostics import public_sync_failure

router = APIRouter(prefix="/api/v1")
DbSession = Annotated[Session, Depends(get_session)]
MobileAuth = Annotated[str, Depends(require_mobile_bearer)]


def _source_observation(session: Session, source_key: str | None) -> SourceObservation | None:
    if not source_key:
        return None
    snapshot_id, separator, external_id = source_key.partition(":")
    if not separator or not snapshot_id or not external_id:
        return None
    return session.scalar(
        select(SourceObservation).where(
            SourceObservation.snapshot_id == snapshot_id,
            SourceObservation.external_id == external_id,
        )
    )


def _safe_payload(observation: SourceObservation | None) -> dict[str, object]:
    if observation is None:
        return {}
    try:
        payload = json.loads(observation.payload_json)
    except (TypeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _reconciliation_identity_details(session: Session, item) -> dict[str, object]:
    left_payload = _safe_payload(_source_observation(session, item.left_source_key))
    right_payload = _safe_payload(_source_observation(session, item.right_source_key))
    cbk_legal = str(left_payload.get("legal_name") or "")
    cbk_trading = left_payload.get("trading_name")
    odpc_name = str(right_payload.get("name") or "")
    if not right_payload:
        basis = "not_located"
    elif cbk_legal and normalize_legal_name(cbk_legal) == normalize_legal_name(odpc_name):
        basis = "normalized_legal_name_exact"
    elif cbk_trading and normalize_legal_name(str(cbk_trading)) == normalize_legal_name(odpc_name):
        basis = "normalized_trading_name_exact"
    else:
        basis = "legal_name_fuzzy"
    return {
        "match_basis": basis,
        "auto_confirmed": bool(
            item.review_state == "confirmed"
            and item.reviewed_by == "system:auto_identity_threshold_v1"
        ),
        "cbk": {
            "legal_name": cbk_legal or None,
            "trading_name": cbk_trading,
            "website": left_payload.get("website"),
            "emails": left_payload.get("emails") or [],
            "licensed_date": left_payload.get("licensed_date"),
        },
        "odpc": (
            {
                "name": right_payload.get("name"),
                "registration_number": right_payload.get("registration_number"),
                "handler_type": right_payload.get("handler_type"),
                "status": right_payload.get("status"),
                "status_as_at": right_payload.get("status_as_at"),
                "county": right_payload.get("county"),
                "country": right_payload.get("country"),
            }
            if right_payload
            else None
        ),
    }


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}


@router.get("/system/status")
def system_status() -> dict[str, object]:
    settings = get_settings()
    return {
        "release_stage": "alpha",
        "local_first": True,
        "telemetry": settings.mobile_telemetry_enabled,
        "sensitive_logging": False,
        "mobile_shared_data": "derived_features_only",
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
            detail={
                "source_id": source_id,
                "code": "manifest_unavailable",
                "message": "KDR source metadata is unavailable or invalid. Repair/rebuild the local stack and retry.",
            },
        ) from exc

    try:
        result = sync_source(
            source,
            store=SnapshotStore(Path(settings.snapshot_dir)),
            session=session,
        )
        session.commit()
    except UnsupportedSourceParser as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "source_id": source_id,
                "code": "unsupported_parser",
                "message": "This source does not yet have an enabled importer.",
            },
        ) from exc
    except (SourceFetchError, SourceParseError, OSError, ValueError) as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=public_sync_failure(source_id, exc),
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
    result = []
    for item in ReconciliationRepository(session).list(limit=safe_limit):
        result.append(
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
                **_reconciliation_identity_details(session, item),
            }
        )
    return result


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


@router.get("/mobile/status")
def mobile_status(_: MobileAuth) -> dict[str, object]:
    return {
        "enabled": True,
        "model_version": MODEL_VERSION,
        "accepted_payload": "derived_features_only",
        "raw_message_storage": False,
    }


@router.post("/mobile/telemetry", status_code=status.HTTP_201_CREATED)
def mobile_telemetry(
    payload: MobileTelemetryEvent,
    session: DbSession,
    _: MobileAuth,
) -> dict[str, object]:
    repository = MobileTelemetryRepository(session)
    item = repository.add(payload)
    server_result = classify_features(payload.features)
    session.commit()
    return {
        "accepted": True,
        "event_id": item.id,
        "server_classification": {
            "label": server_result.label,
            "confidence": server_result.confidence,
            "model_version": server_result.model_version,
        },
    }


@router.post("/mobile/telemetry/batch", status_code=status.HTTP_201_CREATED)
def mobile_telemetry_batch(
    payload: MobileTelemetryBatch,
    session: DbSession,
    _: MobileAuth,
) -> dict[str, object]:
    repository = MobileTelemetryRepository(session)
    labels: dict[str, int] = {}
    for event in payload.events:
        repository.add(event)
        result = classify_features(event.features)
        labels[result.label] = labels.get(result.label, 0) + 1
    session.commit()
    return {
        "accepted": len(payload.events),
        "server_labels": labels,
        "model_version": MODEL_VERSION,
    }


@router.post("/mobile/telemetry/{event_id}/label")
def label_mobile_telemetry(
    event_id: str,
    payload: MobileLabelUpdate,
    session: DbSession,
    _: MobileAuth,
) -> dict[str, object]:
    try:
        item = MobileTelemetryRepository(session).label(event_id, payload.label)
        session.commit()
    except KeyError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail="telemetry event not found") from exc
    return {"event_id": item.id, "user_label": item.user_label}


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
