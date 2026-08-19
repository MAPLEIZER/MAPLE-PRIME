from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.schemas.apps import PlayAppImportItem

_GENERIC_MAIL_DOMAINS = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "yahoo.com",
        "yahoo.co.uk",
        "outlook.com",
        "hotmail.com",
        "live.com",
        "icloud.com",
        "proton.me",
        "protonmail.com",
    }
)


def canonical_email(value: str) -> str:
    return value.strip().lower()


def email_domain(value: str) -> str | None:
    canonical = canonical_email(value)
    if canonical.count("@") != 1:
        return None
    domain = canonical.rsplit("@", 1)[1].strip(".")
    return domain or None


def corporate_domain_from_email(value: str) -> str | None:
    domain = email_domain(value)
    if domain is None or domain in _GENERIC_MAIL_DOMAINS:
        return None
    return domain


def domain_from_url(value: str | None) -> str | None:
    if not value:
        return None
    host = (urlparse(value).hostname or "").lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _name(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


@dataclass(frozen=True)
class OwnershipCandidateScore:
    confidence: float
    signals: tuple[str, ...]
    review_state: str = "candidate"


def score_ownership_candidate(
    app: PlayAppImportItem,
    *,
    institution_legal_name: str,
    institution_trading_name: str | None,
    institution_website: str | None,
    institution_public_emails: tuple[str, ...] = (),
) -> OwnershipCandidateScore:
    score = 0.0
    signals: list[str] = []

    institution_domain = domain_from_url(institution_website)
    developer_domain = domain_from_url(app.developer_website)
    privacy_domain = domain_from_url(app.privacy_policy_url)
    support_email = canonical_email(app.support_email or "")
    support_domain = corporate_domain_from_email(support_email)
    official_emails = {canonical_email(value) for value in institution_public_emails if value.strip()}

    # Exact regulator-published contact reuse is valuable even when the Play
    # developer/app names are generic. It is still evidence, not auto-confirmation.
    if support_email and support_email in official_emails:
        score += 0.60
        signals.append("cbk_published_email_exact")
    if institution_domain and developer_domain == institution_domain:
        score += 0.45
        signals.append("website_domain_exact")
    if institution_domain and support_domain == institution_domain:
        score += 0.35
        signals.append("support_email_domain_exact")
    if institution_domain and privacy_domain == institution_domain:
        score += 0.25
        signals.append("privacy_policy_domain_exact")

    legal = _name(institution_legal_name)
    trading = _name(institution_trading_name)
    developer = _name(app.developer_name)
    app_name = _name(app.app_name)
    if developer and developer == legal:
        score += 0.25
        signals.append("developer_name_legal_exact")
    elif developer and trading and developer == trading:
        score += 0.2
        signals.append("developer_name_trading_exact")
    if trading and app_name == trading:
        score += 0.15
        signals.append("app_name_trading_exact")

    return OwnershipCandidateScore(
        confidence=round(min(score, 0.98), 4),
        signals=tuple(signals),
    )
