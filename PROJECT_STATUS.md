# Project status

**Release track:** `0.1.0-alpha`  
**Development branch:** `agent/alpha-0-30`  
**Release state:** implementation-complete candidate; hands-on machine acceptance pending

## Implemented

### Engineering and persistence

- modular-monolith repository architecture with explicit domain/service/repository boundaries;
- mandatory RED -> GREEN -> REFACTOR engineering standard and PR checklist;
- FastAPI API with typed request/response contracts;
- SQLAlchemy persistence model, repositories and reversible Alembic migrations;
- runtime-aware Alembic configuration so migrations and the application use the same database target;
- documented schema-evolution rules for additive/change/removal migrations;
- committed npm lockfiles plus pip-compiled API/installer dependency locks;
- separate production-only API runtime dependency lock for deterministic container builds;
- Dependabot, CodeQL and CI concurrency controls.

### Privacy and security

- local AES-GCM encrypted vault primitive with Scrypt-derived keys and tamper detection;
- SSRF-oriented outbound URL validation plus official-host allowlisting;
- source fetcher with HTTPS-only policy, redirects disabled and bounded response sizes;
- immutable SHA-256 content-addressed source snapshots;
- separate explicit localhost mutation guards for source sync, reconciliation and manual review;
- CORS regression test preventing foreign origins from obtaining authorization for local-action headers;
- non-root API/web containers, read-only filesystems, dropped Linux capabilities and `no-new-privileges` defaults;
- deterministic non-root UID/GID and isolated writable SQLite/snapshot directories;
- Docker build contexts excluding local secrets, databases, evidence and build/test output;
- reproducible Docker dependency installation (`npm ci` and locked Python runtime dependencies).

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

### Web application

- lightweight shadcn-compatible React/Tailwind dashboard using small source-owned primitives;
- persisted dashboard source/status counts rather than hard-coded regulator values;
- guarded CBK + ODPC sync workflow from the local dashboard;
- reconciliation runs only after both alpha sources sync successfully;
- data-backed reconciliation report with provenance keys and manual review controls;
- Vite and nginx same-origin `/api` proxy paths for consistent local development/container behavior.

### Installer and self-test

- themed Rich terminal UI under `tools/installer`;
- one-file PyInstaller build path for Windows, macOS and Linux;
- user-scoped source installation with Docker/Compose preflight;
- menu-driven Install, Start, Self-test, Open dashboard, Status, Update, Repair, Stop and Uninstall actions;
- normal stop/update/repair/uninstall preserve the persistent KDR Docker volume;
- destructive volume purge requires a separate choice plus a second confirmation;
- bounded GitHub source download, bounded extraction/member count, path-traversal rejection and ZIP-symlink rejection;
- atomic source replacement with rollback on install/update failure;
- API internal self-test for database, approved source manifest and snapshot storage;
- installer self-test covers Docker CLI/daemon/Compose, direct API, web root, nginx->API proxy, API internal integrity and persistence;
- release workflow packages installer binaries, APKs and SHA-256 checksums.

### Android application

- native Kotlin + Jetpack Compose shell under `apps/android`;
- compatibility floor `minSdk 23` (Android 6.0), target/compile API 36;
- separate `direct` and `play` build flavors;
- Play flavor declares no SMS/Call Log permission and supports explicit Android Share intake;
- direct flavor declares `READ_SMS` and `READ_CALL_LOG` for private/sideload testing;
- direct scan starts only after an explicit foreground button action and runtime permission request;
- no SMS/call receiver, service, scheduled worker or automatic background communication scan;
- provider loops continually check foreground state and stop when the activity pauses;
- scan results are memory-only and cleared on foreground loss;
- scan bounded to 250 SMS rows + 250 call rows from the last 90 days;
- call duration is not queried;
- SMS bodies are immediately reduced in memory and never written to KDR storage/logs/API;
- minimizer retains phone identifiers plus service-like labels while discarding ordinary sentence words;
- community upload from Android scan results remains deliberately disabled pending explicit consent/review workflow;
- server contribution contract remains limited to minimized, separately consented mapping metadata rather than raw communications;
- direct APK respects Android hard-restricted permission allowlisting and does not attempt to bypass installer/role controls.

### Validation and documentation

- CI lanes for API, web, TypeScript mobile-core, Windows/macOS/Linux installer builds, native Android direct/play builds and hardened Docker Compose runtime smoke tests;
- CodeQL analysis for Python and JavaScript/TypeScript;
- SRS, architecture, roadmap, threat model, provenance, tech-stack, schema-evolution, engineering-standard, installation, Android and mobile-privacy documentation;
- release workflow capable of producing cross-platform installer artifacts, both Android APK variants and SHA-256 checksum manifest after tagging.

## Only remaining release gate: hands-on machine acceptance

The automated implementation/release-hardening work is complete enough that the remaining alpha gate is a **real-machine acceptance pass**. This intentionally combines the items CI cannot truthfully prove from a hosted runner:

1. run the packaged installer on a normal personal Windows/macOS/Linux machine with Docker;
2. verify themed TUI install/start/status/open/self-test/update/repair/stop/uninstall behavior;
3. verify data survives Docker/app restart, installer repair and non-purge uninstall/reinstall;
4. run a live CBK source sync and verify the current expected 252-record directory invariant against the downloaded snapshot;
5. run the live ODPC source sync and record current public-site/anti-bot behavior without bypassing controls;
6. if both source syncs succeed, inspect a representative sample of CBK ↔ ODPC reconciliation findings for parser/matching drift;
7. install the Android `direct` APK on a personal/test Android 6.0+ device and test explicit foreground scanning;
8. record device/OEM behavior if Android's hard-restricted SMS/Call Log policy prevents a grant; verify KDR reads nothing and Share intake still works;
9. verify scan results disappear when KDR leaves the foreground and are not restored on reopen;
10. verify the permission-free `play` APK/Share workflow independently.

See [`docs/INSTALLATION.md`](docs/INSTALLATION.md) and [`docs/ANDROID.md`](docs/ANDROID.md) for the exact acceptance checklists.

After this pass, the release process is: address any machine-specific defects, switch the installer's default source channel from the alpha branch to `master`, merge PR #1, and create the first public alpha tag/release.

## Deliberately deferred beyond 0–30 alpha

- SMTP/IMAP request delivery and reply correlation;
- provider-specific Playwright automation;
- high-risk identity-document storage;
- uploading Android SMS/Call Log-derived observations before explicit consent/review and local DCP mapping are complete;
- Google Play distribution of the restricted-permission direct flavor;
- complete ODPC enforcement/court ingestion and case linking;
- richer CRB/CIP ingestion and subject-specific evidence import;
- hosted multi-user mode, tenant isolation and KMS-backed envelope encryption.

No public hosted instance should accept other users' sensitive data until the roadmap go/no-go security and Kenyan compliance gates pass.
