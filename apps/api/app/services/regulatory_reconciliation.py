from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.services.cbk_dcp import DcpDirectoryRecord
from app.services.odpc_registry import OdpcHandlerRecord
from app.services.reconcile import normalize_legal_name

AUTO_CONFIRM_THRESHOLD = 0.90
MAX_FUZZY_CANDIDATES = 400


@dataclass(frozen=True)
class RegulatoryFinding:
    cbk_sequence: int
    cbk_legal_name: str
    finding_type: str
    confidence: float
    summary: str
    review_state: str = "pending"
    requires_manual_review: bool = True
    odpc_registration_number: str | None = None
    odpc_name: str | None = None
    odpc_roles: tuple[str, ...] = ()
    match_basis: str = "not_located"


@dataclass(frozen=True)
class _IndexedOdpcRecord:
    record: OdpcHandlerRecord
    normalized_name: str
    tokens: frozenset[str]
    position: int


def _candidate_score(cbk: DcpDirectoryRecord, odpc: OdpcHandlerRecord) -> tuple[float, str]:
    legal = normalize_legal_name(cbk.legal_name)
    odpc_name = normalize_legal_name(odpc.name)
    if legal and legal == odpc_name:
        return 0.96, "normalized_legal_name_exact"
    if cbk.trading_name and normalize_legal_name(cbk.trading_name) == odpc_name:
        return 0.90, "normalized_trading_name_exact"
    ratio = SequenceMatcher(None, legal, odpc_name).ratio()
    if ratio >= 0.90:
        return round(ratio * 0.90, 6), "legal_name_fuzzy"
    return 0.0, "no_match"


def _build_indexes(
    odpc_records: list[OdpcHandlerRecord],
) -> tuple[
    dict[str, list[_IndexedOdpcRecord]],
    dict[str, list[_IndexedOdpcRecord]],
    list[_IndexedOdpcRecord],
]:
    by_name: dict[str, list[_IndexedOdpcRecord]] = defaultdict(list)
    by_token: dict[str, list[_IndexedOdpcRecord]] = defaultdict(list)
    indexed: list[_IndexedOdpcRecord] = []
    for position, record in enumerate(odpc_records):
        normalized = normalize_legal_name(record.name)
        item = _IndexedOdpcRecord(
            record=record,
            normalized_name=normalized,
            tokens=frozenset(token for token in normalized.split() if len(token) >= 3),
            position=position,
        )
        indexed.append(item)
        if normalized:
            by_name[normalized].append(item)
        for token in item.tokens:
            by_token[token].append(item)
    return dict(by_name), dict(by_token), indexed


def _first_exact(
    cbk: DcpDirectoryRecord,
    by_name: dict[str, list[_IndexedOdpcRecord]],
) -> tuple[float, str, OdpcHandlerRecord] | None:
    legal = normalize_legal_name(cbk.legal_name)
    if legal and legal in by_name:
        return 0.96, "normalized_legal_name_exact", by_name[legal][0].record
    trading = normalize_legal_name(cbk.trading_name or "")
    if trading and trading in by_name:
        return 0.90, "normalized_trading_name_exact", by_name[trading][0].record
    return None


def _fuzzy_candidates(
    cbk: DcpDirectoryRecord,
    by_token: dict[str, list[_IndexedOdpcRecord]],
) -> list[OdpcHandlerRecord]:
    legal = normalize_legal_name(cbk.legal_name)
    tokens = frozenset(token for token in legal.split() if len(token) >= 3)
    if not tokens:
        return []

    candidate_map: dict[int, _IndexedOdpcRecord] = {}
    overlap: dict[int, int] = defaultdict(int)
    for token in tokens:
        for item in by_token.get(token, ()):
            candidate_map[item.position] = item
            overlap[item.position] += 1

    ranked = sorted(
        candidate_map.values(),
        key=lambda item: (
            -overlap[item.position],
            abs(len(item.normalized_name) - len(legal)),
            item.position,
        ),
    )
    return [item.record for item in ranked[:MAX_FUZZY_CANDIDATES]]


def _best_match(
    cbk: DcpDirectoryRecord,
    by_name: dict[str, list[_IndexedOdpcRecord]],
    by_token: dict[str, list[_IndexedOdpcRecord]],
) -> tuple[float, str, OdpcHandlerRecord | None]:
    exact = _first_exact(cbk, by_name)
    if exact is not None:
        return exact

    best_score = 0.0
    best_basis = "no_match"
    best: OdpcHandlerRecord | None = None
    for record in _fuzzy_candidates(cbk, by_token):
        score, basis = _candidate_score(cbk, record)
        if score > best_score:
            best_score, best_basis, best = score, basis, record
    return best_score, best_basis, best


def reconcile_cbk_odpc(
    cbk_records: list[DcpDirectoryRecord], odpc_records: list[OdpcHandlerRecord]
) -> list[RegulatoryFinding]:
    findings: list[RegulatoryFinding] = []
    by_name, by_token, _indexed = _build_indexes(odpc_records)

    roles_by_identity: dict[tuple[str, str], tuple[str, ...]] = {}
    role_accumulator: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in odpc_records:
        key = (row.registration_number, normalize_legal_name(row.name))
        if row.handler_type not in role_accumulator[key]:
            role_accumulator[key].append(row.handler_type)
    roles_by_identity = {key: tuple(value) for key, value in role_accumulator.items()}

    for cbk in cbk_records:
        best_score, match_basis, best = _best_match(cbk, by_name, by_token)
        if best is None or best_score < 0.80:
            findings.append(
                RegulatoryFinding(
                    cbk_sequence=cbk.sequence,
                    cbk_legal_name=cbk.legal_name,
                    finding_type="not_located",
                    confidence=1.0,
                    summary=(
                        "Matching ODPC record not located in the reviewed source snapshot. "
                        "This is an evidence gap, not a finding of non-registration or non-compliance."
                    ),
                    match_basis="not_located",
                )
            )
            continue

        roles = roles_by_identity.get(
            (best.registration_number, normalize_legal_name(best.name)), ()
        )
        auto_confirm = best_score >= AUTO_CONFIRM_THRESHOLD and match_basis in {
            "normalized_legal_name_exact",
            "normalized_trading_name_exact",
        }
        findings.append(
            RegulatoryFinding(
                cbk_sequence=cbk.sequence,
                cbk_legal_name=cbk.legal_name,
                finding_type="candidate_match",
                confidence=best_score,
                summary=(
                    "Automatically confirmed because an exact normalized legal/trading name "
                    "matched across the current CBK and ODPC snapshots and met the 90% identity threshold."
                    if auto_confirm
                    else "Candidate CBK ↔ ODPC match — manual review required before confirmation."
                ),
                review_state="confirmed" if auto_confirm else "pending",
                requires_manual_review=not auto_confirm,
                odpc_registration_number=best.registration_number,
                odpc_name=best.name,
                odpc_roles=roles,
                match_basis=match_basis,
            )
        )
    return findings
