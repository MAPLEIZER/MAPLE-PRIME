# Schema Evolution Guide

KDR is designed so database changes remain routine rather than becoming architectural events.

## Source of truth

- `apps/api/app/db/models.py` defines the current application model.
- `apps/api/migrations/versions/` defines how existing installations reach that model.
- repository classes isolate queries from endpoint/domain code.
- migration tests prove a clean database can upgrade and downgrade.

Do not modify a deployed SQLite/PostgreSQL schema manually.

## Required workflow

Schema work follows the same RED -> GREEN -> REFACTOR rule as application code.

1. Add a test describing the new persistence behavior.
2. For structural changes, add/adjust a migration round-trip or data-migration test.
3. Change the SQLAlchemy model.
4. Generate a candidate migration:

```bash
cd apps/api
alembic revision --autogenerate -m "describe change"
```

5. Review the generated SQL/revision manually. Autogenerate output is never accepted blindly.
6. Run:

```bash
alembic upgrade head
pytest -q
ruff check app tests migrations
```

7. For a destructive change, test downgrade or explicitly document why downgrade is unsafe.

## Easy additions

New nullable/additive columns and new tables are preferred. A new field must document:

- purpose;
- sensitivity classification;
- whether it contains personal data;
- retention behavior;
- source/provenance if regulator-derived;
- whether it may appear in logs/exports.

## Renaming a field

Do not rename a heavily used column in a single deployment once users exist. Use expand/migrate/contract:

1. add the new column;
2. deploy code that can read old and new values;
3. backfill data;
4. switch writes to the new column;
5. verify;
6. remove the old column in a later release.

## Deleting a field

Deletion requires proof that the data is no longer required and a retention/privacy review. Remove application reads first, then writes, then the database field in a later migration.

## Changing semantics

Never silently reuse a field for a different meaning. Add a new field/table or a schema-versioned payload. Regulatory facts need immutable provenance; changes in interpretation should create new observations rather than rewriting historical source facts.

## JSON usage

JSON is appropriate for immutable raw/source payloads and audit detail where the schema is source-dependent. Core queryable concepts such as institution identity, request state and verification state remain typed columns.

## Local SQLite to hosted PostgreSQL

Application logic must avoid SQLite-specific behavior. Integration tests for PostgreSQL become mandatory before hosted mode. Alembic revisions must support both engines or explicitly branch with tested dialect-specific operations.

## Migration safety gates

A migration is blocked when it:

- drops personal data without a retention/deletion decision;
- changes a regulatory observation without preserving provenance;
- makes a non-null column without a safe existing-data strategy;
- performs an unbounded destructive backfill during application startup;
- requires manual SQL but provides no tested procedure;
- cannot explain rollback/recovery.
