# Kenya Data Rights

**Status:** pre-alpha / architecture scaffold

Kenya Data Rights (KDR) is a local-first, open-source platform for exercising personal-data and credit-data rights in Kenya while maintaining auditable regulatory intelligence about institutions that may hold personal information.

The first release focuses on **CBK-licensed Digital Credit Providers (DCPs)**, with cross-referencing against the **ODPC public data-handler registry**, **CRB participation/submission evidence**, ODPC determinations, and Kenya Law court decisions.

KDR is not a blacklist and does not assume that a regulated institution improperly holds personal data. It separates:

- regulator listing/licensing status;
- ODPC controller/processor registration observations;
- CRB regulatory/subscriber status;
- subject-specific evidence that an institution submitted a particular person's credit information;
- enforcement decisions and later court outcomes.

An unmatched record means **"not located in the reviewed public source snapshot"**, not "unregistered", "unlicensed", or "non-compliant".

## Why this project exists

Generic tools such as Incogni/DeleteMe focus heavily on US/EU data brokers and people-search sites. Kenya has a different high-value problem: consumers interact with regulated lenders, DCPs, banks, CRBs, payment providers and other institutions whose data-processing obligations intersect with the Data Protection Act, sector regulation and credit-reporting rules.

The current CBK DCP directory used during project research was updated **9 July 2026** and contained **252 licensed DCPs**. This project treats the official source as authoritative and stores snapshot provenance rather than hard-coding regulatory conclusions.

## MVP capabilities

- Import and version CBK DCP directory snapshots.
- Import ODPC registered/deregistered data-handler observations.
- Reconcile entities using deterministic evidence first and fuzzy matching only for review candidates.
- Track CRB regulatory status separately from subject-specific submission evidence.
- Browse ODPC enforcement history and linked court outcomes.
- Create an encrypted local identity profile.
- Generate access, rectification, erasure, restriction, objection, marketing-suppression and CRB-dispute requests.
- Require preview/approval before first submission.
- Send requests through email; add Playwright adapters only where justified.
- Track replies, evidence, deadlines and manual actions.
- Export reproducible CSV/PDF-style reports.
- Run locally with SQLite; migrate to PostgreSQL for hosted multi-user mode.

## Architecture

```text
Browser -> React UI -> FastAPI
                     |-> Regulatory DB (SQLite/Postgres)
                     |-> Encrypted identity vault
                     |-> Rights/request engine
                     |-> Audit event log

Scheduler -> job table -> worker
                        |-> SMTP/OAuth
                        |-> Playwright
                        |-> manual-action queue

Source ETL -> CBK / ODPC / CRB public sources / ODPC determinations / Kenya Law
          -> immutable source snapshots -> normalized observations -> reconciliation
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/SRS.md](docs/SRS.md), and [docs/ROADMAP.md](docs/ROADMAP.md).

## Repository layout

```text
apps/
  api/          FastAPI API
  web/          React/Vite dashboard
  worker/       scheduled/background jobs
packages/
  regulatory_data/
  rights_engine/
  identity_vault/
  reporting/
registry/
  cbk/ odpc/ crb/ cases/
providers/
  kenya/        institution-specific automation adapters
sources/
  source-manifest.yaml
docs/
  SRS.md
  ARCHITECTURE.md
  ROADMAP.md
  THREAT-MODEL.md
  DATA-PROVENANCE.md
  adr/
```

## Local development

### API

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

### Web

```bash
cd apps/web
npm install
npm run dev
```

### Docker Compose

```bash
docker compose -f deploy/docker-compose/compose.yaml up --build
```

The local default binds the API to localhost and uses SQLite. Hosted mode is intentionally not the default.

## Source policy

Primary sources are preferred and must be snapshotted with retrieval time and SHA-256 before normalization. Current source definitions include:

- Central Bank of Kenya DCP directory
- ODPC registered and deregistered data handlers
- ODPC determinations
- Kenya Law legislation and judgments
- CBK CRB/CIP materials

See [sources/source-manifest.yaml](sources/source-manifest.yaml) and [docs/DATA-PROVENANCE.md](docs/DATA-PROVENANCE.md).

## Safety and legal boundaries

KDR helps users organize and exercise rights. It does not decide that a record is unlawful, provide legal representation, or automatically accuse an institution of misconduct.

Requests are targeted. Bulk indiscriminate deletion campaigns are not an MVP feature. Identity documents should remain manual/ephemeral unless an institution specifically requires them.

Before hosting this for other users, follow the go/no-go controls in [docs/ROADMAP.md](docs/ROADMAP.md) and [docs/THREAT-MODEL.md](docs/THREAT-MODEL.md).

## Licence

Apache License 2.0. See [LICENSE](LICENSE).
