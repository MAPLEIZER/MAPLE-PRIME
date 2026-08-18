from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from app.services.cbk_dcp import DcpDirectoryRecord
from app.services.odpc_registry import OdpcHandlerRecord
from app.services.reconcile import normalize_legal_name


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


def _candidate_score(cbk: DcpDirectoryRecord, odpc: OdpcHandlerRecord) -> float:
    legal = normalize_legal_name(cbk.legal_name)
    odpc_name = normalize_legal_name(odpc.name)
    if legal and legal == odpc_name:
        return 0.96
    if cbk.trading_name and normalize_legal_name(cbk.trading_name) == odpc_name:
        return 0.90
    ratio = SequenceMatcher(None, legal, odpc_name).ratio()
    return round(ratio * 0.90, 6) if ratio >= 0.90 else 0.0


def reconcile_cbk_odpc(
    cbk_records: list[DcpDirectoryRecord],
    odpc_records: list[OdpcHandlerRecord],
) -> list[RegulatoryFinding]:
    findings: list[RegulatoryFinding] = []
    for cbk in cbk_records:
        scored = sorted(
            ((_candidate_score(cbk, record), record) for record in odpc_records),
            key=lambda item: item[0],
            reverse=True,
        )
        best_score, best = scored[0] if scored else (0.0, None)
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
        findings.append(
            RegulatoryFinding(
                cbk_sequence=cbk.sequence,
                cbk_legal_name=cbk.legal_name,
                finding_type="candidate_match",
                confidence=best_score,
                summary="Candidate CBK ↔ ODPC match — manual review required before confirmation.",
                odpc_registration_number=best.registration_number,
                odpc_name=best.name,
                odpc_roles=roles,
            )
        )
    return findings
