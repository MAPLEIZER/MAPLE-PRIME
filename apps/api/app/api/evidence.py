from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.local_actions import (
    require_evidence_review_action,
    require_evidence_upload_action,
    require_relationship_action,
)
from app.core.config import get_settings
from app.db.evidence_repository import EvidenceDocumentRepository
from app.db.relationship_repository import EntityRelationshipRepository
from app.db.session import get_session
from app.schemas.evidence import EvidenceDocumentReviewInput
from app.schemas.relationships import RelationshipEvidenceInput
from app.services.brs_evidence import (
    MAX_BRS_PDF_BYTES,
    extract_brs_claims,
    extract_pdf_text,
    store_brs_pdf,
)

router = APIRouter(prefix="/api/v1/evidence", tags=["evidence documents"])
DbSession = Annotated[Session, Depends(get_session)]
DocumentTypeHeader = Annotated[str, Header(alias="X-KDR-Document-Type")]


def _serialize(item) -> dict[str, object]:
    return {
        "id": item.id,
        "sha256": item.sha256,
        "document_type": item.document_type,
        "source_authority": item.source_authority,
        "page_count": item.page_count,
        "company_name": item.company_name,
        "registration_number": item.registration_number,
        "application_number": item.application_number,
        "verification_state": item.verification_state,
        "verified_by": item.verified_by,
        "verified_at": item.verified_at.isoformat() if item.verified_at else None,
        "created_at": item.created_at.isoformat(),
    }


@router.get("/brs")
def list_brs_documents(session: DbSession) -> list[dict[str, object]]:
    return [_serialize(item) for item in EvidenceDocumentRepository(session).list()]


@router.post("/brs", dependencies=[Depends(require_evidence_upload_action)])
async def upload_brs_document(
    request: Request,
    session: DbSession,
    document_type: DocumentTypeHeader,
) -> dict[str, object]:
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BRS_PDF_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="PDF exceeds 10 MB")
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/pdf":
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="application/pdf required")
    data = await request.body()
    try:
        stored = store_brs_pdf(
            data,
            document_type=document_type,
            storage_root=Path(get_settings().snapshot_dir),
        )
        text, page_count = extract_pdf_text(data)
        claims = extract_brs_claims(text)
        item = EvidenceDocumentRepository(session).record(
            sha256=stored.sha256,
            document_type=document_type,
            storage_path=str(stored.storage_path),
            page_count=page_count,
            claims=claims,
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception:
        session.rollback()
        raise
    return _serialize(item)


@router.post("/brs/{document_id}/review", dependencies=[Depends(require_evidence_review_action)])
def review_brs_document(
    document_id: str,
    payload: EvidenceDocumentReviewInput,
    session: DbSession,
) -> dict[str, object]:
    try:
        item = EvidenceDocumentRepository(session).review(
            document_id,
            decision=payload.decision,
            reviewer="local_user",
        )
        session.commit()
    except KeyError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found") from exc
    return _serialize(item)


@router.post(
    "/brs/{document_id}/attach/{relationship_id}",
    dependencies=[Depends(require_relationship_action)],
)
def attach_brs_document(
    document_id: str,
    relationship_id: str,
    session: DbSession,
) -> dict[str, object]:
    documents = EvidenceDocumentRepository(session)
    relationships = EntityRelationshipRepository(session)
    document = documents.get(document_id)
    relationship = relationships.get(relationship_id)
    if document is None or relationship is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document or relationship not found")
    claims = json.loads(document.extracted_claims_json)
    evidence = relationships.add_evidence(
        relationship.id,
        RelationshipEvidenceInput(
            source_type="brs_uploaded_official_search",
            observed_at=document.created_at.replace(tzinfo=document.created_at.tzinfo or UTC),
            evidence_strength=(
                "very_strong" if document.verification_state == "manual_verified" else "strong"
            ),
            evidence_text=f"BRS {document.document_type} document hash {document.sha256}",
            structured_claim={
                "document_id": document.id,
                "sha256": document.sha256,
                "verification_state": document.verification_state,
                **claims,
            },
        ),
    )
    session.commit()
    return {
        "relationship_id": relationship.id,
        "evidence_id": evidence.id,
        "evidence_fingerprint": evidence.evidence_fingerprint,
    }


@router.get("/brs/verification-guidance")
def brs_verification_guidance() -> dict[str, object]:
    return {
        "automatic_public_api_available": False,
        "reason": "BRS output verification currently requires an application number and interactive security-question answer.",
        "official_verify_url": "https://manual.brs.go.ke/verify",
        "official_search_url": "https://brsv2.ecitizen.go.ke/",
        "beneficial_ownership_form_url": "https://brs.go.ke/forms/",
        "researched_at": datetime(2026, 8, 19, tzinfo=UTC).isoformat(),
    }
