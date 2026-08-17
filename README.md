# Kenya Data Rights

**Status:** pre-alpha / architecture scaffold

Kenya Data Rights (KDR) is a local-first, open-source platform for exercising personal-data and credit-data rights in Kenya while maintaining auditable regulatory intelligence about institutions that may hold personal information.

The first release focuses on **CBK-licensed Digital Credit Providers (DCPs)**, with cross-referencing against the **ODPC public data-handler registry**, **CRB participation/submission evidence**, ODPC determinations, and Kenya Law court decisions.

KDR is not a blacklist and does not assume that a regulated institution improperly holds personal data. It separates regulator licensing, ODPC registration observations, CRB regulatory/subscriber status, subject-specific CRB evidence, and enforcement/court outcomes.

An unmatched record means **"not located in the reviewed public source snapshot"**, not "unregistered", "unlicensed", or "non-compliant".

## MVP

- Version CBK DCP directory snapshots.
- Import ODPC registered/deregistered data-handler observations.
- Reconcile entities conservatively with provenance and confidence.
- Keep CRB regulatory status separate from evidence that a lender submitted a specific user's data.
- Track ODPC enforcement history and linked court outcomes.
- Create an encrypted local identity profile.
- Generate access, rectification, erasure, restriction, objection, marketing-suppression and CRB-dispute requests.
- Require preview/approval before transmission.
- Track replies, evidence, deadlines and manual actions.
- Run locally first; PostgreSQL/multi-user hosted mode comes later.

## Stack

React/Vite dashboard + FastAPI API + local SQLite, with a separate worker for email/browser automation and source ETL. Docker Compose is the reference self-hosted deployment.

See `docs/SRS.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/THREAT-MODEL.md`, and `docs/DATA-PROVENANCE.md`.

## Licence

Apache-2.0.
