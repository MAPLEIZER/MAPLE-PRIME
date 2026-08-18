# Project status

**Release track:** `0.1.0-alpha`  
**Development branch:** `agent/alpha-0-30`

## Implemented

- modular-monolith repository architecture;
- mandatory test-first engineering standard and PR checklist;
- FastAPI API and conservative rights/reconciliation services;
- SQLAlchemy persistence model, repositories and reversible Alembic migration;
- local AES-GCM encrypted vault primitive with Scrypt key derivation;
- SSRF-oriented outbound URL validation;
- immutable SHA-256 content-addressed source snapshot store;
- source manifest with authoritative CBK/ODPC/CRB/Kenya Law sources;
- parser for the actual multiline CBK DCP directory text structure;
- ODPC public registered-handler HTML table parser;
- conservative entity matching and CRB evidence-boundary model;
- shadcn-compatible React/Tailwind dashboard shell with small source-owned UI primitives;
- mobile privacy domain core that strips local communication content before a contribution can be shared;
- GitHub CI for API, web and mobile-core tests/builds/audits;
- CodeQL workflow and Dependabot configuration;
- SRS, architecture, roadmap, threat model, provenance, tech-stack, schema-evolution and mobile-privacy documentation.

## 0–30 alpha work still open

- controlled network fetcher with redirect/DNS protections and snapshot persistence;
- PDF text extraction adapter and full ingest verification against all 252 entries in the 9 July 2026 CBK directory;
- end-to-end ODPC registry sync into versioned observations;
- persisted CBK ↔ ODPC reconciliation report and manual-resolution workflow;
- first real source sync/status API backed by the database rather than reference values;
- Docker fresh-install integration test;
- lockfiles/reproducible dependency locks before a tagged public alpha release.

## Deliberately deferred

- SMTP/IMAP request delivery;
- provider-specific Playwright automation;
- identity-document storage;
- restricted SMS/Call Log permission use;
- complete enforcement/court ingestion;
- hosted multi-user mode.

No public hosted instance should accept other users' sensitive data until the roadmap go/no-go security and Kenyan compliance gates pass.
