# regulatory_data

Parsers, source snapshotting, normalization, entity reconciliation and discrepancy generation live here as this scaffold matures.

Rules:

1. Preserve source bytes or a verifiable snapshot reference before parsing.
2. Store source publication/effective date separately from retrieval time.
3. Never overwrite historical observations.
4. Do not turn "not matched" into a non-compliance finding.
5. Fuzzy matching generates review candidates; it does not create legal facts.
