from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.core.config import get_settings
from app.schemas.civic import CivicDraftRequest
from app.services.civic_participation import (
    ConsultationRegistry,
    build_mailto_link,
    draft_memorandum,
)
from app.services.legal_library import load_legal_library, search_legal_library

router = APIRouter(prefix="/api/v1")


def _legal_entries():
    settings = get_settings()
    return load_legal_library(Path(settings.legal_library_path))


def _consultations() -> ConsultationRegistry:
    settings = get_settings()
    return ConsultationRegistry.load(Path(settings.civic_registry_path))


@router.get("/legal/library")
def legal_library() -> list[dict[str, object]]:
    try:
        return [entry.as_dict() for entry in _legal_entries()]
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="legal library is unavailable") from exc


@router.get("/legal/search")
def legal_search(q: str = Query(min_length=2, max_length=200), limit: int = 10) -> list[dict[str, object]]:
    try:
        entries = _legal_entries()
        results = search_legal_library(entries, q, limit=max(1, min(limit, 50)))
        return [entry.as_dict() for entry in results]
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="legal library is unavailable") from exc


@router.get("/civic/consultations")
def civic_consultations() -> list[dict[str, object]]:
    try:
        return [item.model_dump() for item in _consultations().consultations]
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="consultation registry is unavailable") from exc


@router.post("/civic/consultations/{consultation_id}/draft")
def civic_draft(consultation_id: str, payload: CivicDraftRequest) -> dict[str, object]:
    if payload.consultation_id != consultation_id:
        raise HTTPException(status_code=400, detail="consultation id mismatch")
    try:
        consultation = _consultations().get(consultation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="consultation not found") from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="consultation registry is unavailable") from exc

    draft = draft_memorandum(consultation, payload)
    submission_allowed = consultation.status == "open"
    mailto_links: list[dict[str, str]] = []
    form_links: list[dict[str, str]] = []
    if submission_allowed:
        for channel in consultation.channels:
            if channel.kind == "email":
                mailto_links.append({"label": channel.label, "url": build_mailto_link(channel, draft)})
            elif channel.kind == "form" and channel.url:
                form_links.append({"label": channel.label, "url": channel.url})

    return {
        "subject": draft.subject,
        "body": draft.body,
        "sent": False,
        "requires_user_review": True,
        "submission_allowed": submission_allowed,
        "mailto_links": mailto_links,
        "form_links": form_links,
        "anti_spam": "KDR never bulk-submits or sends without a user action.",
    }
