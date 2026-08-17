# ADR 0005: Local-first encrypted identity vault

**Status:** Accepted

## Decision

Regulatory browsing works without identity data. Personal identity is stored as an application-encrypted payload with keys separated from the database.

## Rationale

The system should not become a centralized collection of precisely the information users are trying to protect. Hosted mode is a later security/compliance phase, not the development default.
