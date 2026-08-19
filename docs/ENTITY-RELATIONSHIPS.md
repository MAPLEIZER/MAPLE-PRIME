# Entity Relationships and Ownership Evidence

KDR does not treat `owner` as one overloaded fact. The alpha relationship graph records typed claims between apps, institutions and externally referenced entities while keeping the evidence append-only.

Supported relationship types are:

- `published_by`
- `developed_by`
- `operated_by`
- `lends_on_behalf_of`
- `trading_name_of`
- `licensed_as`
- `data_controller_is`
- `subsidiary_of`
- `parent_company_is`
- `beneficially_owned_by`

Every edge begins as `candidate`. Confirmation or rejection changes the review state of the edge, not the source evidence.

Evidence records can reference a public HTTPS URL, a KDR immutable source snapshot and/or a regulator/source observation. The original evidence is never rewritten when a reviewer changes a conclusion.

## Legacy ownership backfill

The existing `app_ownership_links` table remains during the alpha for compatibility. A local backfill endpoint converts those candidate links into `marketplace_app -> operated_by -> institution` edges and records the individual match signals as evidence.

```text
POST /api/v1/relationships/backfill/app-ownership
X-KDR-Local-Action: record_relationship
```

Exact Play/CBK email/domain matches remain evidence only. They do not auto-confirm an operator relationship.

## BRS and beneficial ownership

A BRS document or official-search result should be stored as evidence for a corporate relationship, not as a mutable `owner` field. Where KDR has an immutable copy of the uploaded document, the evidence row should carry the snapshot reference, document hash and extracted structured claim. A reviewer can then confirm a `subsidiary_of`, `parent_company_is` or `beneficially_owned_by` edge without altering the uploaded source.

Beneficial-owner records should use an external reference until KDR has an appropriate privacy-reviewed entity model for natural persons. Public exports must not expose unnecessary personal identifiers.
