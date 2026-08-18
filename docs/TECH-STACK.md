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

## Mobile

The alpha mobile track is a **pure TypeScript domain core**, not yet a permission-heavy native application.

A later Android/iOS shell may use React Native/Expo after platform-policy review, but the mobile domain boundary is already fixed:

- classification should occur on-device wherever possible;
- raw SMS bodies, contact books, call recordings and unrestricted call logs are not accepted by the KDR server API;
- a shared contribution is separately consented mapping metadata only;
- Play-distributed builds must not request restricted SMS/Call Log permissions merely to crowdsource mappings.

See `docs/MOBILE-PRIVACY-ARCHITECTURE.md`.

## Source ingestion

```text
manifest -> controlled fetch -> immutable raw snapshot -> extraction -> parser
         -> normalized observation -> reconciliation candidate -> manual/verified link
```

Each step is replaceable. A regulator changing a PDF or HTML layout should require a parser change, not a database redesign.

Raw source snapshots are content-addressed by SHA-256 and carry source/retrieval provenance.

## Worker

Background work stays in the same Python codebase initially. Jobs will be persisted and executed by a separate worker process when scheduling/email/browser automation is introduced. The worker must not receive vault master secrets unless its task explicitly requires them.

## Deployment

- local development: native Python/Node tooling;
- reference self-host: Docker Compose;
- alpha database: SQLite on a persistent local volume;
- future hosted mode: PostgreSQL, isolated worker, encrypted object storage, managed secrets/KMS and reverse proxy/TLS.

## Dependency policy

- JavaScript application dependencies are exact-pinned and a lockfile is required before tagged public releases.
- Python dependencies use bounded compatible ranges during alpha; a reproducible lock/constraints file is required before public beta.
- CI runs tests, builds and dependency/security checks.
- No dependency is added only for convenience when a small auditable standard-library implementation is sufficient.

## Schema policy

SQLAlchemy models are the application model; Alembic revisions are the deployment history. Every schema modification follows test-first migration rules and the expand/migrate/contract pattern where destructive changes are involved.

See `docs/SCHEMA-EVOLUTION.md`.
