from app.services.crb import RegulatoryCrbStatus, SubjectSubmissionStatus, safe_public_summary


def test_no_evidence_is_not_non_submission_claim():
    text = safe_public_summary(
        RegulatoryCrbStatus.MANDATORY_SUBSCRIBER,
        SubjectSubmissionStatus.NO_EVIDENCE,
    )
    assert "does not establish" in text
