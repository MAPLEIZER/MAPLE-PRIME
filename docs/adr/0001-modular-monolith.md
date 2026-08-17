# ADR 0001: Start as a modular monolith

**Status:** Accepted

## Decision

Use React/Vite + FastAPI + SQLite locally, with a separate worker process and SQL-backed jobs. PostgreSQL is the hosted-mode database.

## Rationale

The MVP needs auditable workflows and safe source handling, not distributed-systems complexity. This keeps deployment and maintenance realistic for one developer and ordinary hardware.
