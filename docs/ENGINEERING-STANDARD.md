# Engineering Standard

## Priority order

1. Correct functionality and code quality.
2. Security and privacy.
3. Testability and maintainability.
4. Performance and convenience.

No feature may trade away the first two priorities for delivery speed.

## Test-first rule

All behavioral changes follow RED -> GREEN -> REFACTOR:

1. Define the user-visible or security acceptance criterion.
2. Add or change a test that demonstrates the criterion and fails for the intended reason.
3. Commit the failing test when practical so the development history preserves the contract.
4. Implement the smallest correct change that makes the test pass.
5. Refactor without changing behavior.
6. Run the full affected suite plus security/static checks.

A bug fix begins with a regression test. A database migration begins with a migration/round-trip test. A parser change begins with a fixture test. A security control begins with positive and negative tests. Exceptions are limited to documentation-only changes, generated files, or emergencies and must be explained in the PR.

## Architecture rules

- Keep a modular monolith. Do not introduce a network service boundary without an ADR.
- Domain logic must not import FastAPI, React, SMTP, Playwright, or a database driver directly.
- Persistence is behind repositories; external sources are behind adapters.
- Schema changes only through versioned Alembic migrations. Never edit a deployed database manually.
- Every persisted field has a documented purpose, retention class, and sensitivity class.
- Source-derived regulatory facts always carry provenance and snapshot identifiers.
- Fuzzy matching creates review candidates, never legal/compliance conclusions.
- Raw SMS bodies, call recordings, contact books, and unrestricted call logs are outside the shared-data model.

## Definition of done

A change is complete only when tests pass, migrations are reversible or explicitly documented as irreversible, sensitive-data flows are reviewed, public API/schema changes are documented, and no secret or real-person evidence appears in fixtures or logs.
