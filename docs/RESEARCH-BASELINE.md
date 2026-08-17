# Regulatory Research Baseline — 17 August 2026

This document converts the project's August 2026 research into implementation assumptions. It is not a substitute for re-syncing the primary sources.

## CBK DCP baseline

The research baseline used the Central Bank of Kenya **Directory of Digital Credit Providers — July 2026**, updated 9 July 2026. The directory contained **252 licensed DCP entries** and published legal names, contacts/addresses and licensing dates.

Primary source:

- https://www.centralbank.go.ke/wp-content/uploads/2026/07/Directory-of-Digital-Credit-Providers-July-2026.pdf

Implementation consequence: the source importer must preserve the exact PDF snapshot and should assert parser invariants such as continuous entry numbering before accepting a new version.

## ODPC baseline

The ODPC public data-handler register exposes fields including handler name, handler type (controller/processor), registration number, location and status. The research environment could not safely claim that a complete 252-DCP reconciliation had been captured, so the repository treats exhaustive ODPC synchronization as unfinished production work.

Primary sources:

- https://www.odpc.go.ke/registered-data-handlers/
- https://www.odpc.go.ke/deregistered-data-handlers/

Implementation consequence: absence from a reviewed snapshot is stored as an evidence gap, not proof of non-registration.

## CRB baseline

CBK materials distinguish mandatory subscribers from approved third-party credit information providers. A DCP's absence from a public third-party CIP directory cannot establish that the DCP does not submit credit information.

Primary sources:

- https://www.centralbank.go.ke/bank-supervision/
- https://www.centralbank.go.ke/wp-content/uploads/2025/05/Approved-Third-Party-Credit-Information-Providers-31-December-2024.pdf

Implementation consequence: keep `regulatory_crb_status` separate from `subject_specific_submission_status`. Subject-specific submission evidence should come from the user's own CRB material or another authorized source.

## Data-rights baseline

The rights engine is grounded in Kenya's Data Protection Act and related regulations, while sector-specific financial rules may require retention of records even where an erasure request is made.

Primary sources:

- https://new.kenyalaw.org/akn/ke/act/2019/24/eng@2022-12-31
- https://new.kenyalaw.org/akn/ke/act/ln/2021/263/eng@2022-12-31
- https://new.kenyalaw.org/akn/ke/act/ln/2022/46/eng@2022-04-22

Implementation consequence: access, rectification, restriction, objection, direct-marketing suppression, consent withdrawal, erasure and CRB dispute are separate workflows.

## Enforcement/court baseline

Research identified lending-related ODPC determinations and later court proceedings. These must not be flattened into a single "bad/good provider" field.

Examples used to validate the case model include:

- **Whitepath Company Ltd:** ODPC determination dated 29 January 2025 included liability findings, an enforcement notice and KES 450,000 compensation. Primary ODPC PDF: https://www.odpc.go.ke/wp-content/uploads/2025/03/FRIDAH-KEMUNTO-OBUBA-vs-WHITEPATH-COMPANY-LIMITED.pdf
- **Ceres Tech Ltd:** a High Court judgment dated 7 May 2026 allowed the provider's appeal and set aside the relevant ODPC determination. Primary Kenya Law judgment: https://new.kenyalaw.org/akn/ke/judgment/kehc/2026/6200/eng@2026-05-07

Implementation consequence: store administrative determination, appeal/judicial-review proceeding and current procedural effect as separate linked records.

## Language rules

Approved language:

- "No sufficiently confident ODPC match was located in the reviewed snapshot."
- "Current CBK directory match found."
- "Court outcome requires manual verification."
- "Subject-specific CRB submission evidence not imported."

Disallowed automatic language:

- "unregistered" based only on reconciliation failure;
- "unlicensed" based only on alias/name mismatch;
- "does not submit to CRBs" based on public directory absence;
- "violated the law" without a verified decision supporting the statement.
