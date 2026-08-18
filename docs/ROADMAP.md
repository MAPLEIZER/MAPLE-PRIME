# Roadmap

## Product sequence

The first useful product is **regulatory intelligence + targeted rights workflow**, not a mass-removal bot.

## 0–30 days: local alpha foundation

### Engineering foundation

- [x] Enforce RED -> GREEN -> REFACTOR in repository guidance and PR template.
- [x] Establish modular-monolith boundaries and repository pattern.
- [x] Replace unbounded frontend dependency versions with exact versions.
- [x] Add API/web/mobile CI and dependency audits.
- [x] Add CodeQL and Dependabot baseline.
- [ ] Commit reproducible npm/Python lock artifacts before tagged alpha.

### Regulatory data

- [x] Implement immutable snapshot store and SHA-256 provenance.
- [x] Implement parser for the official CBK DCP multiline record format.
- [ ] Implement controlled CBK PDF fetch + extraction adapter.
- [ ] Run full parser invariants against the current 252-entry directory snapshot.
- [x] Implement ODPC registered-handler table parser.
- [ ] Persist a complete ODPC registered/deregistered source sync without anti-bot bypasses.
- [x] Add canonical institution/alias model.
- [x] Keep deterministic evidence and review-only fuzzy reconciliation separate.
- [x] Keep CRB regulatory status separate from subject-specific submission evidence.
- [ ] Generate persisted CBK ↔ ODPC reconciliation findings with manual resolution.

### Application

- [x] FastAPI application and versioned API boundary.
- [x] Lightweight shadcn-compatible React/Tailwind dashboard shell.
- [x] Rights-request types/state definitions and preview service.
- [x] SQLite persistence, repository layer and reversible Alembic migration.
- [x] Local authenticated-encryption vault primitive.
- [x] Source/provenance status presentation in the dashboard.
- [x] Mobile mapping-evidence domain boundary and tests.
- [ ] Back dashboard source status with persisted sync data.
- [ ] Docker fresh-install integration test.

### Alpha exit criteria

- fresh install runs locally from documented commands;
- API, web and mobile-core CI are green;
- CBK source snapshot ingests reproducibly and yields exactly the expected numbered records;
- ODPC sync produces versioned observations;
- cross-reference report can be manually audited and does not label absence as non-compliance;
- no personal identity data is required to use the regulatory explorer;
- encrypted vault round-trip/tamper and migration tests pass;
- raw SMS/call-history content is outside the shared mobile API contract.

## 31–60 days: rights engine and evidence

- [ ] Add data-backed institution detail pages and alias/mapping evidence.
- [ ] Add targeted access/rectification/erasure/objection/marketing/CRB workflows.
- [ ] Require request preview and explicit approval.
- [ ] SMTP/OAuth send adapter.
- [ ] IMAP correlation and sanitized reply parser.
- [ ] Encrypted evidence store and retention rules.
- [ ] Deadline and manual-action scheduler.
- [ ] ODPC determination importer.
- [ ] Case/court linking workflow with manual disposition verification.
- [ ] CSV/JSON/HTML report exports.
- [ ] Begin permission-minimal mobile shell after platform/legal review.

## 61–90 days: automation and public open-source beta

- [ ] Add first provider-specific Playwright adapters based on actual need.
- [ ] Add adapter dry-run and health checks.
- [ ] Add CAPTCHA/manual-intervention state.
- [ ] Harden backup/export/restore.
- [ ] Add signed release process and SBOM.
- [ ] Publish contributor/data-provenance workflow.
- [ ] Recruit limited beta testers who self-host.
- [ ] Resolve parser drift and false-match findings.
- [ ] Expand regulator coverage only after DCP workflow is stable.

### Open-source beta acceptance

- zero known high-severity security findings in supported flows;
- tests cover encryption, matching, parser drift, migrations and request transitions;
- no raw PII in CI, fixtures or logs;
- ODPC/CBK discrepancy reports use conservative language;
- CRB reports distinguish regulatory data from user-specific evidence;
- mobile shared records contain only documented minimal mapping metadata.

## Post-90 days: optional hosted pilot

Do not accept other users' sensitive data until all go/no-go controls pass.

Required work includes PostgreSQL, authentication/recovery, tenant isolation, KMS envelope encryption, worker isolation, encrypted object storage/backups, rate limiting, audit controls, privacy notices/terms, incident response, Kenyan controller/processor/registration review and cloud/cross-border review.

### GO only if

- [ ] independent security review completed;
- [ ] threat-model high-risk findings closed or formally accepted;
- [ ] tenant isolation tested;
- [ ] encryption keys separated from database backups;
- [ ] backup restore tested;
- [ ] ID document handling is ephemeral and explicit;
- [ ] incident/breach response is documented;
- [ ] privacy/terms/subprocessor disclosures are published;
- [ ] Kenyan compliance review completed;
- [ ] operational monitoring is active;
- [ ] deletion/offboarding workflow has been tested.

### NO-GO if

- master secrets are stored beside user ciphertext;
- logs contain request bodies/PII;
- administrators can silently browse user evidence;
- browser automation can read master secrets unnecessarily;
- backups are unencrypted;
- legal conclusions are auto-generated and acted upon without review;
- no proven deletion/retention mechanism exists.

## Expansion priority after DCPs

1. CBK banks, microfinance banks, payment-service providers and CRBs.
2. SASRA-regulated SACCOs with authoritative public lists.
3. IRA-regulated insurers/intermediaries where relevant.
4. CA-regulated communications providers.
5. Employment/recruitment and other high-risk sectors after source/legal workflows are defined.
6. Conventional international people-search/data-broker removals as an optional module.

Being on a regulator list is never itself evidence of improper data processing.
