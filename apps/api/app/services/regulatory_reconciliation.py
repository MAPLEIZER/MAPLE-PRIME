from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from app.services.cbk_dcp import DcpDirectoryRecord
from app.services.odpc_registry import OdpcHandlerRecord
from app.services.reconcile import normalize_legal_name

AUTO_CONFIRM_THRESHOLD = 0.90


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


def reconcile_cbk_odpc(
    cbk_records: list[DcpDirectoryRecord],
    odpc_records: list[OdpcHandlerRecord],
) -> list[RegulatoryFinding]:
    findings: list[RegulatoryFinding] = []
    for cbk in cbk_records:
        scored = sorted(
            ((*_candidate_score(cbk, record), record) for record in odpc_records),
            key=lambda item: item[0],
            reverse=True,
        )
        if scored:
            best_score, match_basis, best = scored[0]
        else:
            best_score, match_basis, best = 0.0, "no_match", None
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

        same_registration = [
            row
            for row in odpc_records
            if row.registration_number == best.registration_number
            and normalize_legal_name(row.name) == normalize_legal_name(best.name)
        ]
        roles = tuple(dict.fromkeys(row.handler_type for row in same_registration))
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
