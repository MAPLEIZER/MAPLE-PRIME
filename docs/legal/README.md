# KDR Legal Library

> **Educational reference, not legal advice.** KDR helps people find authoritative Kenyan privacy, digital-credit and cyber-law sources. It must not label a message, company or event as an unlawful breach unless the legal and factual elements have been separately verified.

The library is structured for humans and future citation-grounded AI:

- readable Markdown chapters live here;
- `index.json` is the canonical searchable metadata index;
- each record points to an authoritative public source and records a source date;
- future AI/RAG features must cite the provision/source used and expose uncertainty;
- legal updates should create reviewable diffs rather than silently replacing prior interpretations.

## Chapters

1. [Constitutional foundations](01-foundations.md)
2. [Data protection](02-data-protection.md)
3. [ODPC procedure and enforcement](03-procedure-enforcement.md)
4. [Digital credit and CRBs](04-digital-credit-crb.md)
5. [Cybercrime](05-cybercrime.md)
6. [Access, consumer and communications law](06-access-consumer-comms.md)
7. [Message triage](07-message-triage.md)
8. [AI readiness](AI-READINESS.md)

The backend exposes `/api/v1/legal/library` and `/api/v1/legal/search?q=...`. A search hit means a source **may be relevant**, not that KDR has determined liability, a breach, an offence or non-compliance.

Baseline reviewed against authoritative sources: **18 August 2026**.
