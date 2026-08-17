# Roadmap

## Product sequence

The first useful product is the **regulatory intelligence + targeted rights workflow**, not a mass-removal bot.

## 0–30 days: local alpha foundation

### Regulatory data

- [ ] Implement snapshot store and SHA-256 provenance.
- [ ] Implement robust CBK DCP PDF importer.
- [ ] Validate current 252-entry directory against parser invariants.
- [ ] Implement ODPC registered/deregistered importer without anti-bot bypasses.
- [ ] Add canonical entity/alias model.
- [ ] Implement deterministic + review-only fuzzy reconciliation.
- [ ] Add CRB regulatory/submission evidence split.

### Application

- [x] Create FastAPI scaffold.
- [x] Create lightweight React dashboard scaffold.
- [x] Define request types/state machine.
- [ ] Add SQLite persistence and migrations.
- [ ] Implement identity vault.
- [ ] Implement source/status pages.

### Exit criteria

- fresh install runs locally;
- CBK snapshot ingests reproducibly;
- ODPC sync produces versioned observations;
- cross-reference report can be manually audited;
- no personal identity data needed to use regulatory explorer.

## 31–60 days: rights engine and evidence

- [ ] Add institution detail pages.
- [ ] Add targeted access/rectification/erasure/objection/marketing/CRB workflows.
- [ ] Require request preview and approval.
- [ ] SMTP/OAuth send adapter.
- [ ] IMAP correlation and sanitized reply parser.
- [ ] Encrypted evidence store and retention rules.
- [ ] Deadline and manual-action scheduler.
- [ ] ODPC determination importer.
- [ ] Case/court linking workflow with manual disposition verification.
- [ ] CSV/JSON/HTML report exports.

### Exit criteria

- a user can complete one end-to-end email rights request locally;
- every material action appears in an audit timeline;
- request/evidence export is reproducible;
- no automated legal satisfaction classification.

## 61–90 days: automation and public open-source beta

- [ ] Add first provider-specific Playwright adapters based on actual need.
- [ ] Add adapter dry-run and health checks.
- [ ] Add CAPTCHA/manual-intervention state.
- [ ] Harden backup/export/restore.
- [ ] Add signed release process, SBOM and dependency scanning.
- [ ] Publish contributor/data-provenance workflow.
- [ ] Recruit limited beta testers who self-host.
- [ ] Resolve parser drift and false-match findings.
- [ ] Add high-value regulator expansions after DCP workflow is stable.

### Open-source beta acceptance

- zero known high-severity security findings in supported flows;
- tests cover encryption, matching, parser drift and request state transitions;
- no raw PII in CI, fixtures or logs;
- ODPC/CBK discrepancy reports use conservative language;
- CRB reports distinguish public regulatory data from user-specific evidence.

## Post-90 days: optional hosted pilot

Do not accept other users' sensitive data until all go/no-go controls below pass.

### Required hosted work

- PostgreSQL migration.
- authentication + recovery strategy.
- tenant isolation.
- KMS/Vault envelope encryption.
- worker isolation.
- object storage encryption.
- encrypted backups + tested restore.
- rate limiting and abuse prevention.
- admin break-glass audit.
- privacy notice, terms, retention schedule and incident response.
- Kenyan legal/privacy review of controller/processor obligations and ODPC registration implications.
- subprocessors/cloud-location review.

## Go/no-go before handling other users' sensitive data

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
- [ ] a deletion/offboarding workflow has been tested.

### NO-GO if

- master secrets are stored beside user ciphertext;
- logs contain request bodies/PII;
- administrators can silently browse user evidence;
- browser automation can read master secrets;
- backups are unencrypted;
- legal conclusions are auto-generated and acted upon without review;
- no proven deletion/retention mechanism exists.

## Expansion priority after DCPs

1. CBK banks, microfinance banks, payment-service providers and CRBs.
2. SASRA-regulated SACCOs where authoritative public lists are available.
3. IRA-regulated insurers/intermediaries where high-value personal data processing is relevant.
4. CA-regulated communications providers.
5. Employment/recruitment and other high-risk sectors only after source/legal workflows are defined.
6. Conventional international people-search/data-broker removals as an optional module.

Being on a regulator list is never itself evidence of improper data processing.

## Solo-developer effort bands

- local regulatory alpha: 60–100 hours;
- rights/email/evidence workflow: 100–170 hours;
- browser adapters + hardening + open beta: 150–230 hours;
- safe multi-user hosted pilot: additional 180–300+ hours.

These are planning bands, not delivery promises.
