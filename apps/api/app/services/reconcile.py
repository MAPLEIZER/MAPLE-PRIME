from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

LEGAL_SUFFIXES = {"ltd", "limited", "plc", "company", "co"}


@dataclass(frozen=True)
class Candidate:
    name: str
    email_domains: frozenset[str] = frozenset()
    phones: frozenset[str] = frozenset()
    addresses: frozenset[str] = frozenset()


def normalize_legal_name(value: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", value.lower())
    while tokens and tokens[-1] in LEGAL_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def score_candidate(left: Candidate, right: Candidate) -> float:
    left_name = normalize_legal_name(left.name)
    right_name = normalize_legal_name(right.name)

    score = 0.0
    if left_name and left_name == right_name:
        score += 0.70
    else:
        score += 0.20 * SequenceMatcher(None, left_name, right_name).ratio()

    if left.email_domains & right.email_domains:
        score += 0.20
    if left.phones & right.phones:
        score += 0.15
    if left.addresses & right.addresses:
        score += 0.10

    return min(score, 1.0)


def classify_score(score: float) -> str:
    score = round(score, 6)
    if score >= 0.95:
        return "auto_match_candidate"
    if score >= 0.80:
        return "manual_review"
    return "unmatched"
