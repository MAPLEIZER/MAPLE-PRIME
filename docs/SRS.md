# Software Requirements Specification (SRS)

**Project:** Kenya Data Rights (KDR)  
**Version:** 0.1  
**Status:** Pre-alpha baseline  
**Date:** 17 August 2026

## 1. Purpose

KDR is a local-first open-source application that helps a Kenyan data subject discover relevant regulated institutions, exercise data-protection and credit-data rights, track evidence and responses, and inspect regulator/court provenance without presenting unverified discrepancies as violations.

## 2. Scope

### In scope for MVP

1. CBK DCP source ingestion and snapshot versioning.
2. ODPC registered/deregistered handler ingestion.
3. CBK↔ODPC entity reconciliation with manual-review queue.
4. CRB regulatory classification and user-imported subject-specific submission evidence.
5. ODPC determination and Kenya Law case metadata.
6. Encrypted local identity profile.
7. Rights workflows: access, rectification, erasure, restriction, objection, marketing suppression, consent withdrawal and CRB dispute.
8. Email-based requests, reply correlation and deadline tracking.
9. Optional provider-specific Playwright adapters.
10. Audit history and report exports.
11. Lightweight React dashboard.
12. Docker Compose self-hosting.

### Explicitly out of MVP

- indiscriminate bulk deletion requests to all institutions;
- automatic legal conclusions or compliance scoring;
- storing users' ID documents by default;
- Kubernetes;
- automated CAPTCHA bypass;
- billing/multi-tenant SaaS;
- automatic court win/loss classification without verified disposition.

## 3. Stakeholders

- Kenyan individual/data subject;
- self-hosting technical user;
- privacy researcher or civil-society analyst;
- maintainer/contributor;
- future managed-hosting operator;
- future reviewer/legal/privacy adviser.

## 4. Functional requirements

### FR-REG Regulatory source management

- **FR-REG-001** The system shall define each authoritative source in a machine-readable source manifest.
- **FR-REG-002** The system shall preserve retrieval timestamp, publication/effective date when known, source URL and SHA-256 for each snapshot.
- **FR-REG-003** The system shall retain historical observations instead of replacing previous source states.
- **FR-REG-004** The CBK importer shall validate basic parser invariants before accepting a snapshot.
- **FR-REG-005** The ODPC importer shall capture registered and deregistered observations separately.
- **FR-REG-006** Source parsing failures shall not silently delete or invalidate prior observations.

### FR-REC Entity reconciliation

- **FR-REC-001** The system shall maintain a canonical regulated-entity identifier independent of regulator naming.
- **FR-REC-002** Exact normalized legal-name matches shall receive greater weight than fuzzy similarity.
- **FR-REC-003** Public email domains, phone numbers and addresses may corroborate a candidate match.
- **FR-REC-004** Fuzzy matching shall only produce candidate matches for review unless confidence and deterministic corroboration meet the automatic threshold.
- **FR-REC-005** An unmatched record shall be labeled "not located in reviewed public snapshot" or equivalent.
- **FR-REC-006** The system shall preserve aliases/trading names and the evidence establishing them.

### FR-CRB Credit-reference evidence

- **FR-CRB-001** The system shall store regulatory CRB participation separately from subject-specific submission evidence.
- **FR-CRB-002** The system shall never infer non-submission merely because a lender is absent from a third-party CIP list.
- **FR-CRB-003** Users shall be able to attach/import evidence indicating which institution supplied their credit information.
- **FR-CRB-004** CRB disputes shall be linked to the specific disputed observation/evidence where possible.

### FR-CASE Enforcement/court history

- **FR-CASE-001** ODPC determinations and court proceedings shall be distinct linked records.
- **FR-CASE-002** The system shall model court effect using a controlled vocabulary such as set-aside, varied, dismissed, pending and procedural-only.
- **FR-CASE-003** Unverified dispositions shall remain `UNKNOWN_REQUIRES_REVIEW`.
- **FR-CASE-004** Case summaries shall link to primary-source provenance.

### FR-ID Identity vault

- **FR-ID-001** Personal identity information shall be encrypted at application level.
- **FR-ID-002** Encryption keys shall not be stored in the same database as encrypted identity data.
- **FR-ID-003** Identity documents shall be optional and ephemeral by default.
- **FR-ID-004** The system shall support complete local-data deletion and encrypted backup/export.

### FR-RGT Rights request workflow

- **FR-RGT-001** A user shall choose a target institution and a specific right/workflow.
- **FR-RGT-002** The system shall generate a preview before the first submission.
- **FR-RGT-003** User approval shall be required before transmission.
- **FR-RGT-004** The system shall track request state, timestamps, responses and evidence.
- **FR-RGT-005** Erasure templates shall state that legally required retention is not being overridden.
- **FR-RGT-006** The system shall support manual-action states for identity checks, CAPTCHAs, unsupported forms and uncertain responses.
- **FR-RGT-007** Escalation packets shall contain the request, delivery evidence, responses, timeline and unresolved issues.

### FR-COM Communications

- **FR-COM-001** Outbound requests shall use unique correlation identifiers.
- **FR-COM-002** Inbound replies shall preserve message metadata and content hash.
- **FR-COM-003** Reply classification shall expose confidence and require review for uncertain/legal conclusions.
- **FR-COM-004** Sensitive attachments shall be encrypted and retention-limited.

### FR-UI Dashboard

- **FR-UI-001** The dashboard shall show source freshness and provenance.
- **FR-UI-002** It shall show regulator coverage without creating a single compliance score.
- **FR-UI-003** It shall provide institution detail pages with CBK, ODPC, CRB and case layers.
- **FR-UI-004** It shall provide request timelines and manual-action queues.
- **FR-UI-005** It shall remain usable on a modest laptop and mobile-width browser.

### FR-REP Reporting

- **FR-REP-001** Reconciliation reports shall include snapshot dates and confidence.
- **FR-REP-002** CSV/JSON exports shall expose evidence/provenance fields.
- **FR-REP-003** Reports shall use conservative discrepancy labels.

## 5. Non-functional requirements

- **NFR-SEC-001:** Local mode binds to loopback by default.
- **NFR-SEC-002:** No telemetry by default.
- **NFR-SEC-003:** Logs must be structured and PII-redacted.
- **NFR-SEC-004:** Browser automation must run without access to master encryption secrets.
- **NFR-SEC-005:** Hosted mode requires authentication, authorization, rate limiting, CSRF/XSS/SSRF controls and tenant isolation.
- **NFR-PRIV-001:** Collect the minimum identity data needed for the chosen request.
- **NFR-PERF-001:** Regulatory browsing should remain responsive with tens of thousands of observations on SQLite/PostgreSQL.
- **NFR-REL-001:** Source updates are append/version based; parser failure cannot destroy prior data.
- **NFR-AUD-001:** Material user/request events form an append-only audit sequence.
- **NFR-MAINT-001:** Institution-specific web automation is isolated from core domain logic.
- **NFR-PORT-001:** Self-hosted release supports Linux/macOS/Windows via Docker where feasible.

## 6. Core data entities

- `regulated_entity`
- `entity_alias`
- `source_snapshot`
- `regulator_observation`
- `cbk_dcp_listing`
- `odpc_registration`
- `crb_regulatory_status`
- `subject_crb_evidence`
- `enforcement_case`
- `court_case`
- `identity_profile`
- `campaign`
- `rights_request`
- `message`
- `automation_run`
- `evidence`
- `audit_event`

## 7. Request state model

```text
DRAFT
 -> AWAITING_APPROVAL
 -> READY
 -> SENT
 -> AWAITING_RESPONSE
 -> RESPONSE_RECEIVED
 -> SATISFIED_PENDING_VERIFICATION -> CLOSED
 -> ESCALATION_REVIEW

Any executable stage -> MANUAL_REQUIRED -> previous/next valid stage
```

No state transition implying legal satisfaction may be performed solely by an LLM.

## 8. External interfaces

- CBK public web/PDF sources
- ODPC public web/PDF sources
- Kenya Law public legislation/judgment sources
- SMTP/OAuth outbound email
- IMAP or signed inbound mail webhook
- institution web forms via Playwright
- user-provided CRB reports/evidence

## 9. API baseline

```text
GET  /api/v1/health
GET  /api/v1/dashboard/summary
GET  /api/v1/entities
GET  /api/v1/entities/{id}
GET  /api/v1/reconciliation/findings
POST /api/v1/reconciliation/{id}/resolve
POST /api/v1/rights/preview
POST /api/v1/rights/requests
POST /api/v1/rights/requests/{id}/approve
POST /api/v1/rights/requests/{id}/send
GET  /api/v1/rights/requests/{id}/timeline
POST /api/v1/evidence
POST /api/v1/sources/sync
GET  /api/v1/reports/reconciliation
```

Only the first three scaffold endpoints are implemented in pre-alpha.

## 10. Acceptance criteria for self-hosted MVP

The release is MVP-ready when a clean install can:

1. sync a CBK DCP snapshot and preserve provenance;
2. sync ODPC public handler data;
3. produce a manual-reviewable cross-match report;
4. represent CRB status/evidence without false non-submission inference;
5. browse enforcement/court records with verified provenance;
6. create an encrypted identity profile;
7. preview and approve a targeted rights request;
8. send email and correlate the reply;
9. pause cleanly for manual/CAPTCHA actions;
10. export an evidence/report bundle;
11. pass security/unit/integration tests;
12. run under Docker Compose without external SaaS dependencies.

## 11. Legal/product constraints

The application is a rights-management and evidence tool, not a substitute for legal advice. Hosted operation involving other users' personal data requires a separate Kenyan compliance review before launch, including controller/processor role analysis, ODPC registration obligations where applicable, breach handling, processor/subprocessor arrangements, retention, cloud location and cross-border considerations.
