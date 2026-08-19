# BRS Corporate Evidence

## Current public path researched 2026-08-19

The Business Registration Service currently lists a paid **Official Search (Companies)** that issues a CR12, and its forms library includes **FORM LBOF6 — Beneficial Ownership Official Search Request**. A user can therefore obtain an official output themselves and upload it to local KDR rather than KDR paying for every company search.

BRS also exposes an output-verification page, but the public page requires service selection, an application number and an interactive security-question answer. KDR did not find a documented public verification API. The alpha therefore does not claim unattended BRS verification.

## KDR upload model

KDR accepts a local PDF as either:

- `brs_cr12`; or
- `brs_beneficial_ownership_search`.

The PDF is bounded to 10 MB, SHA-256 content-addressed and stored with restrictive local permissions. KDR extracts only organization/document identifiers into queryable metadata by default: company name, registration number, application number and whether the document is a beneficial-ownership search. Names/IDs/phones/addresses of natural-person beneficial owners remain inside the local source PDF unless a future privacy-reviewed workflow explicitly needs them.

A document begins as `uploaded_unverified`. A user can check the output on the official BRS verification page and mark it `manual_verified`; that review changes KDR's conclusion, not the immutable source bytes/hash.

A BRS document can be attached to an entity relationship as evidence. A manually verified official search is treated as `very_strong` evidence; an uploaded but unverified official-looking document remains `strong` evidence and does not auto-confirm a beneficial-owner relationship.
