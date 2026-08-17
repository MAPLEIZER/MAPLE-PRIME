# ADR 0004: Separate CRB regulatory status from subject-specific submission evidence

**Status:** Accepted

## Decision

Maintain `regulatory_crb_status` independently from `subject_specific_submission_status`.

## Rationale

Public third-party CIP directories do not answer whether a particular DCP actually submitted a particular user's credit data. Subject-specific claims require user/bureau evidence.
