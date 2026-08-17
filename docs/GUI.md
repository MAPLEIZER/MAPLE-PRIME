# Dashboard / GUI Specification

The UI is intentionally restrained. It is an evidence dashboard, not a full CRM.

## Navigation

```text
Overview
Institutions
My Requests
Cases
Reports
Sources
Settings
```

## Overview

```text
+-----------------------------------------------------------------------+
| Kenya Data Rights                              Source sync: <timestamp> |
+-------------+---------------------------------------------------------+
| Navigation  |  Regulatory overview                                    |
|             |                                                         |
|             |  [CBK DCPs] [ODPC sync] [Open requests] [Manual review] |
|             |                                                         |
|             |  Source coverage                 Attention               |
|             |  CBK        Ready                unmatched review        |
|             |  ODPC       <state>              stale source            |
|             |  CRB        <state>              court review            |
|             |  Kenya Law  <state>                                      |
|             |                                                         |
|             |  Recent rights requests                                  |
+-------------+---------------------------------------------------------+
```

## Institution detail

```text
<Canonical legal name>                   [CBK status] [ODPC observation]

Official records
  CBK listing / licence date / published contact
  ODPC controller registration(s)
  ODPC processor registration(s)
  source snapshot history

Credit information
  Regulatory CRB status
  My imported submission evidence
  Disputes/corrections

Enforcement and court history
  ODPC determination -> linked court proceeding -> current effect

My relationship
  used provider? yes/no/unsure
  account/reference (encrypted/private)

Actions
  Access | Rectify | Erasure | Restrict | Object | Stop marketing | CRB dispute
```

## Reconciliation report

Columns:

```text
canonical entity
CBK status / licence date
ODPC controller registration
ODPC processor registration
CRB regulatory status
subject evidence state
case count
current court effect
match confidence
finding code
source snapshot dates
```

Filters:

- high-confidence matches;
- manual-review candidates;
- no located public match;
- deregistered-observation conflicts;
- duplicate/shared published contacts;
- stale sources;
- enforcement/court-history present.

## Visual language

- neutral grey/charcoal base;
- status chips use words, not color alone;
- no "risk score" gauge;
- warnings explain evidence limitations;
- source date always visible near regulatory facts;
- empty states teach the evidence boundary rather than push users into bulk actions.

The current `apps/web` scaffold implements the overview shell responsively with no heavy charting library.
