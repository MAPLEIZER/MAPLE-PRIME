from enum import StrEnum


class RegulatoryCrbStatus(StrEnum):
    MANDATORY_SUBSCRIBER = "mandatory_subscriber"
    APPROVED_THIRD_PARTY = "approved_third_party"
    UNKNOWN = "unknown"


class SubjectSubmissionStatus(StrEnum):
    SUBMITTED_MY_DATA = "submitted_my_data"
    NO_EVIDENCE = "no_evidence"
    DISPUTED = "disputed"
    CORRECTED = "corrected"
    UNKNOWN = "unknown"


def safe_public_summary(
    regulatory_status: RegulatoryCrbStatus,
    subject_status: SubjectSubmissionStatus,
) -> str:
    """Keep regulatory classification separate from personal reporting evidence."""
    if subject_status == SubjectSubmissionStatus.SUBMITTED_MY_DATA:
        return "Subject-specific evidence indicates this institution supplied credit data."
    if subject_status == SubjectSubmissionStatus.NO_EVIDENCE:
        return (
            "No subject-specific submission evidence has been imported. "
            "This does not establish that the institution does not submit to CRBs."
        )
    return f"Regulatory CRB status: {regulatory_status}; subject evidence: {subject_status}."
