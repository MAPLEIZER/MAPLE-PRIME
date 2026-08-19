# Technology Stack

This document is the stack contract for Kenya Data Rights (KDR). Changing a foundational technology requires an Architecture Decision Record (ADR), migration plan and tests.

## Architecture style

**Modular monolith, local-first.** The web UI, API, persistence, source ingestion, rights engine and worker are separate modules in one repository. A network service boundary is introduced only when isolation or scale demonstrably requires it.

This keeps deployment simple for self-hosters and prevents premature microservice coupling.

## Backend

| Layer | Choice | Role |
|---|---|---|
| Runtime | Python 3.12 | Stable application/runtime baseline |
| HTTP API | FastAPI | Typed API and OpenAPI contract |
| Validation | Pydantic v2 | Boundary validation and explicit schemas |
| ORM | SQLAlchemy 2 | Persistence mapping and repository layer |
| Migrations | Alembic | Versioned, reviewable schema changes |
| Local database | SQLite | Zero-admin local/self-hosted alpha |
| Hosted database | PostgreSQL | Future multi-user deployment only |
| HTTP client | HTTPX | Controlled regulator/source access |
| Cryptography | `cryptography` | AES-GCM authenticated encryption and supported primitives |
| YAML | PyYAML | Versioned source manifest |
| Tests | pytest | Unit, contract, migration and security tests |
| Static checks | Ruff | Lint/import/modernization checks |

### Persistence boundary

Domain/application code does not issue arbitrary SQL. Database access is placed behind repository classes. This permits changes to table layout without spreading persistence assumptions through endpoints and parsers.

## Web application

| Layer | Choice | Role |
|---|---|---|
| UI runtime | React 19 | Component model |
| Language | TypeScript 7 | Strict UI/domain contracts |
| Build tool | Vite 8 | Small, fast Vite application |
| UI system | shadcn-compatible local components | Source-owned UI primitives rather than a runtime UI framework |
| Styling | Tailwind CSS 4 | Utility styling and design tokens |
| Icons | Lucide React | Small consistent icon set |
| Tests | Vitest | Domain and component contract tests |

The web app uses the official shadcn Vite/dashboard/sidebar patterns as composition references. KDR copies only the primitives it uses. It intentionally does **not** pull a large admin-dashboard framework, chart package or data-grid package into alpha.

## Android application

The Android alpha is a native Kotlin + Jetpack Compose shell under `apps/android`.

| Layer | Choice | Role |
|---|---|---|
| Language | Kotlin (AGP built-in Kotlin) | Native Android application logic |
| Compose compiler | Kotlin plugin 2.3.21 | Compose compiler aligned to Kotlin |
| UI | Jetpack Compose + Material 3 | Modern declarative mobile UI |
| Compatibility floor | API 23 / Android 6.0 | Broad device coverage with maintained current AndroidX |
| Target / compile | API 36 | Current platform and distribution target |
| Build | Android Gradle Plugin 9.3.0 + Gradle 9.5.0 | Published stable, documented compatible native build |
| JDK | Temurin/OpenJDK 17 | AGP-supported toolchain |
| Tests | JUnit | Privacy/domain/build contracts |
| Distribution flavors | `direct`, `play` | Restricted-permission sideload build separated from permission-free Play build |

AGP 9.x enables built-in Kotlin, so KDR intentionally does not apply the legacy `org.jetbrains.kotlin.android` plugin. The Compose compiler plugin remains explicitly versioned because Compose compilation is a separate Kotlin plugin concern.

The `direct` flavor can request `READ_SMS` and `READ_CALL_LOG` only after an explicit foreground action. It has no communication receiver/service and its provider loops terminate when the activity loses foreground status. Raw SMS/call rows are not a persistence model.

The `play` flavor declares neither restricted permission and retains the explicit Android Share workflow.

The server boundary remains stricter than the direct-device capability: raw SMS bodies and unrestricted call-log records are not accepted by the KDR contribution API.

See `docs/ANDROID.md` and `docs/MOBILE-PRIVACY-ARCHITECTURE.md`.

## Mobile domain core

`apps/mobile` remains a pure TypeScript privacy/domain package independent of the Android UI. It models minimization and contribution boundaries that may later be reused by other mobile shells.

Core invariants:

- classification should occur on-device wherever possible;
- raw SMS bodies, contact books, call recordings and unrestricted call logs are not accepted by the KDR server API;
- a shared contribution is separately consented mapping metadata only;
- restricted-device access and server contribution are separate trust boundaries.

## Source ingestion

```text
manifest -> controlled fetch -> immutable raw snapshot -> extraction -> parser
         -> normalized observation -> reconciliation candidate -> manual/verified link
```

Each step is replaceable. A regulator changing a PDF or HTML layout should require a parser change, not a database redesign.

Raw source snapshots are content-addressed by SHA-256 and carry source/retrieval provenance.

## Worker

Background work stays in the same Python codebase initially. Jobs will be persisted and executed by a separate worker process when scheduling/email/browser automation is introduced. The worker must not receive vault master secrets unless its task explicitly requires them.

## Desktop installer

`tools/installer` is a deliberately small Python 3.12 package using **Rich** for the themed terminal UI and **PyInstaller** for one-file executables.

It does not replace the deployment architecture. It safely orchestrates the existing Docker Compose stack and provides:

- Docker/Compose preflight;
- install/start/stop/update/repair;
- browser launch;
- data-preserving uninstall;
- separately confirmed destructive purge;
- external and API-internal self-tests.

CI builds the installer on Windows, macOS and Linux so end users do not need Python, Node.js or Git for the normal executable path.

See `docs/INSTALLATION.md`.

## Deployment

- simplest local install: packaged KDR Installer executable + Docker;
- local development: native Python/Node/Android tooling;
- reference self-host: Docker Compose;
- alpha database: SQLite on a persistent local volume;
- future hosted mode: PostgreSQL, isolated worker, encrypted object storage, managed secrets/KMS and reverse proxy/TLS.

## Dependency policy

- JavaScript application dependencies are exact-pinned and committed npm lockfiles are consumed with `npm ci`.
- Python API/dev and installer dependency graphs are pip-compiled into committed transitive lock files; the API also has a production-only runtime lock used by Docker.
- Android plugin/BOM/toolchain versions are explicitly pinned in Gradle configuration.
- Installer dependencies are locked; the executable is rebuilt on each release platform rather than treated as a portable Python environment.
- CI runs tests, builds and dependency/security checks.
- No dependency is added only for convenience when a small auditable standard-library implementation is sufficient.

## Schema policy

SQLAlchemy models are the application model; Alembic revisions are the deployment history. Every schema modification follows test-first migration rules and the expand/migrate/contract pattern where destructive changes are involved.

See `docs/SCHEMA-EVOLUTION.md`.
