from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import SourceObservation, SourceSnapshot
from app.services.app_registry import domain_from_url


def build_cbk_discovery_seeds(session: Session) -> dict[str, object]:
    snapshot = session.scalar(
        select(SourceSnapshot)
        .where(SourceSnapshot.source_id == "cbk_dcp")
        .order_by(SourceSnapshot.retrieved_at.desc(), SourceSnapshot.id.desc())
        .limit(1)
    )
    if snapshot is None:
        return {"snapshot_id": None, "source_url": None, "retrieved_at": None, "records": []}

    observations = list(
        session.scalars(
            select(SourceObservation)
            .where(SourceObservation.snapshot_id == snapshot.id)
            .order_by(SourceObservation.external_id, SourceObservation.id)
        )
    )
    records: list[dict[str, object]] = []
    for observation in observations:
        payload = json.loads(observation.payload_json)
        legal_name = str(payload.get("legal_name") or "").strip()
        trading_name_raw = payload.get("trading_name")
        trading_name = str(trading_name_raw).strip() if trading_name_raw else None
        website_raw = payload.get("website")
        website = str(website_raw).strip() if website_raw else None
        website_domain = domain_from_url(website)
        emails = list(
            dict.fromkeys(
                str(email).strip().lower()
                for email in (payload.get("emails") or [])
                if str(email).strip()
            )
        )
        search_terms = list(
            dict.fromkeys(
                value
                for value in (legal_name, trading_name, website_domain, *emails)
                if value
            )
        )
        records.append(
            {
                "cbk_sequence": payload.get("sequence"),
                "legal_name": legal_name,
                "trading_name": trading_name,
                "website": website,
                "website_domain": website_domain,
                "emails": emails,
                "search_terms": search_terms,
                "source_observation_id": observation.id,
            }
        )

    return {
        "snapshot_id": snapshot.id,
        "source_url": snapshot.source_url,
        "retrieved_at": snapshot.retrieved_at.isoformat(),
        "records": records,
    }
