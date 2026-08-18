from app.services.cbk_dcp import DcpDirectoryRecord
from app.services.odpc_registry import OdpcHandlerRecord
from app.services.regulatory_reconciliation import reconcile_cbk_odpc


def test_exact_legal_name_is_still_a_review_candidate() -> None:
    cbk = [DcpDirectoryRecord(sequence=1, legal_name="Example Credit Limited")]
    odpc = [
        OdpcHandlerRecord(
            sequence=1,
            name="Example Credit Ltd",
            handler_type="Data Controller",
            registration_number="INST-ABC123",
            county="NAIROBI",
            country="Kenya",
            status="Active/Renewed",
            status_as_at="7/9/2026",
        )
    ]
    findings = reconcile_cbk_odpc(cbk, odpc)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.finding_type == "candidate_match"
    assert finding.review_state == "pending"
    assert finding.requires_manual_review is True
    assert finding.odpc_registration_number == "INST-ABC123"
    assert finding.confidence >= 0.9


def test_not_located_uses_non_accusatory_language() -> None:
    cbk = [DcpDirectoryRecord(sequence=1, legal_name="Alpha Credit Limited")]
    odpc = [
        OdpcHandlerRecord(
            sequence=1,
            name="Completely Different Company",
            handler_type="Data Controller",
            registration_number="INST-ZZZ999",
            county=None,
            country="Kenya",
            status="Active/Renewed",
            status_as_at=None,
        )
    ]
    finding = reconcile_cbk_odpc(cbk, odpc)[0]
    assert finding.finding_type == "not_located"
    assert finding.odpc_registration_number is None
    assert "not located" in finding.summary.lower()
    assert "unregistered" not in finding.summary.lower()
    assert "non-compliant" not in finding.summary.lower()


def test_controller_and_processor_roles_are_not_collapsed() -> None:
    cbk = [DcpDirectoryRecord(sequence=1, legal_name="Example Credit Limited")]
    odpc = [
        OdpcHandlerRecord(1, "Example Credit Limited", "Data Controller", "INST-ABC123", None, "Kenya", "Active", None),
        OdpcHandlerRecord(2, "Example Credit Limited", "Data Processor", "INST-ABC123", None, "Kenya", "Active", None),
    ]
    finding = reconcile_cbk_odpc(cbk, odpc)[0]
    assert finding.finding_type == "candidate_match"
    assert finding.odpc_roles == ("Data Controller", "Data Processor")
