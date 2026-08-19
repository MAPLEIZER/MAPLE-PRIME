# ADR-006: Keep raw communications outside the shared mobile data plane

- Status: Accepted
- Date: 2026-08-18

## Context

KDR can become more useful if users help map lender apps, sender IDs and contact channels to the CBK-licensed entities behind them. Raw messages and call histories, however, contain third-party personal data and create unnecessary platform, security and regulatory exposure.

## Decision

Mobile classification is local-first. The hosted/shared API does not accept raw message bodies, unrestricted call logs, contact books or recordings. Community contribution is a distinct opt-in action containing only reduced mapping metadata. Contributions enter the database as unverified evidence and require corroboration/review before becoming trusted mappings.

A Play-distributed application will not request restricted SMS/Call Log permissions for crowdsourced research or enrichment.

## Consequences

- breach impact is materially reduced;
- local use remains possible without contributing data;
- the server cannot perform server-side message NLP on private inboxes;
- users may need to paste/share individual items manually;
- a separate legal assessment is still required before public hosted contribution processing.
