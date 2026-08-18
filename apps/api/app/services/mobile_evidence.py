from __future__ import annotations

import hashlib
import json

from app.schemas.mobile import ContributionCreate, SharedContribution


def prepare_shared_contribution(item: ContributionCreate) -> SharedContribution:
    if not item.share_consent:
        raise ValueError("explicit share consent is required")
    stable = {
        "kind": item.kind.value,
        "institution_hint": item.institution_hint,
        "sender_identifier": item.sender_identifier,
        "app_package": item.app_package,
        "observed_at": item.observed_at.isoformat() if item.observed_at else None,
    }
    fingerprint = hashlib.sha256(
        json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return SharedContribution(**stable, evidence_fingerprint=fingerprint)
