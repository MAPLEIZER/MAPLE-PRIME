# Project status

**Release track:** `0.1.0-alpha`  
**Development branch:** `agent/alpha-0-30`

## Implemented

### Engineering and persistence

- modular-monolith repository architecture with explicit domain/service/repository boundaries;
- mandatory RED -> GREEN -> REFACTOR engineering standard and PR checklist;
- FastAPI API with typed request/response contracts;
- SQLAlchemy persistence model, repositories and reversible Alembic migrations;
- runtime-aware Alembic configuration so migrations and the application use the same database target;
- documented schema-evolution rules for additive/change/removal migrations;
- exact frontend dependency versions, Dependabot, CodeQL and CI concurrency controls.

### Privacy and security

- local AES-GCM encrypted vault primitive with Scrypt-derived keys and tamper detection;
- SSRF-oriented outbound URL validation plus official-host allowlisting;
- source fetcher with HTTPS-only policy, redirects disabled and bounded response sizes;
- immutable SHA-256 content-addressed source snapshots;
- separate explicit localhost mutation guards for source sync, reconciliation and manual review;
- CORS regression test preventing foreign origins from obtaining authorization for local-action headers;
- non-root API/web containers, read-only filesystems, dropped Linux capabilities and no-new-privileges defaults;
- deterministic non-root UID/GID and isolated writable SQLite/snapshot directories;
- Docker build contexts excluding local secrets, databases, evidence and build/test output.

### Regulatory data and reconciliation

- versioned source manifest for authoritative CBK, ODPC, CRB and Kenya Law sources;
- PDF text-extraction adapter and parser for the actual multiline CBK DCP directory format;
- ODPC registered-handler HTML parser preserving controller and processor observations separately;
- fetch -> immutable snapshot -> parser -> versioned source-observation ingestion pipeline;
- expected-record-count support so known directory cardinality can fail closed on parser/source drift;
- conservative CBK ↔ ODPC reconciliation using latest persisted snapshots;
- persisted reconciliation findings tied to exact source snapshot/record keys;
- `candidate_match` and `not_located` semantics that require manual review and do not infer non-compliance;
- manual Confirm/Reject review workflow that changes only local review state, never source evidence;
- CRB regulatory/subscriber status kept separate from subject-specific proof that an institution submitted a person's data.

### Web and mobile foundations

- lightweight shadcn-compatible React/Tailwind dashboard using small source-owned primitives;
- persisted dashboard source/status counts rather than hard-coded regulator values;
- guarded CBK + ODPC sync workflow from the local dashboard;
- reconciliation runs only after both alpha sources sync successfully;
- data-backed reconciliation report with provenance keys and manual review controls;
- Vite and nginx same-origin `/api` proxy paths for consistent local development/container behavior;
- mobile privacy domain core that strips raw communication content before a contribution can be shared;
- server contribution contract limited to minimal, explicitly consented mapping metadata rather than raw SMS, call history, contacts or recordings.

### Validation and documentation

- CI lanes for API, web, mobile-core and hardened Docker Compose runtime smoke tests;
- CodeQL analysis for Python and JavaScript/TypeScript;
- SRS, architecture, roadmap, threat model, provenance, tech-stack, schema-evolution, engineering-standard and mobile-privacy documentation.

## Remaining before a tagged public alpha

- run and preserve a live end-to-end ingest of the current official CBK DCP source and verify all 252 numbered entries against the source snapshot;
- run and preserve a live ODPC registered-handler sync and inspect parser drift/current public-site behavior without bypassing anti-bot controls;
- manually audit a representative sample of live CBK ↔ ODPC findings before treating the reconciliation workflow as field-validated;
- commit reproducible dependency lock artifacts before the first tagged public release;
- keep CI, container smoke tests and both CodeQL languages green on the release commit.

These are validation/release-hardening items. The underlying local alpha ingestion, persistence, reconciliation, review and dashboard paths are implemented.

## Deliberately deferred beyond 0–30 alpha

- SMTP/IMAP request delivery and reply correlation;
- provider-specific Playwright automation;
- high-risk identity-document storage;
- restricted Android SMS/Call Log permission use;
- native mobile application shell and store distribution;
- complete ODPC enforcement/court ingestion and case linking;
- richer CRB/CIP ingestion and subject-specific evidence import;
- hosted multi-user mode, tenant isolation and KMS-backed envelope encryption.

No public hosted instance should accept other users' sensitive data until the roadmap go/no-go security and Kenyan compliance gates pass.
