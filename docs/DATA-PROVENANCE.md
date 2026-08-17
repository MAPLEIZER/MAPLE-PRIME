# Data Provenance and Reconciliation Policy

## Principle

KDR records what an authoritative source published at a point in time. It does not silently "fix" regulator data or collapse different regulatory concepts into one compliance flag.

## Snapshot metadata

Every import stores:

- authority;
- source URL;
- retrieval timestamp;
- publication/effective date where available;
- SHA-256 of source bytes or canonical response;
- parser name/version;
- import result/count;
- validation warnings.

## Entity matching

Priority:

1. hard external identifier where available;
2. exact normalized legal name;
3. corroborating official email domain/phone/address;
4. known trading-name/alias evidence;
5. fuzzy similarity for review candidates only.

Default score guidance:

```text
exact normalized legal name          +0.70
exact official email domain          +0.20
exact phone                          +0.15
strong address overlap               +0.10
verified alias relationship          +0.10
fuzzy legal-name similarity          +0.00–0.20
conflicting hard identifier          reject
```

Suggested actions:

- >=0.95 plus corroboration: automatic candidate match;
- 0.80–0.949: manual review;
- <0.80: unmatched;
- hard-identifier conflict: explicit conflict.

## Discrepancy vocabulary

Permitted examples:

- `CBK_NO_ODPC_MATCH`: no sufficiently confident public ODPC match in reviewed snapshot;
- `ODPC_DCP_LIKE_NO_CBK_MATCH`: ODPC entity resembles DCP/lender but no current exact CBK match;
- `ODPC_DEREGISTERED_CBK_CURRENT`: current CBK entity candidate linked to deregistered ODPC observation — high-priority review, not automatic violation;
- `ODPC_ROLE_PROCESSOR_ONLY`: matched public observation is processor-only — review, not automatic error;
- `SHARED_OFFICIAL_EMAIL`: two source-published legal entities share a contact;
- `FREE_MAIL_CONTACT`: official source uses common free-mail domain — informational;
- `CONTACT_DRIFT`: regulator and institution website contacts differ;
- `ENFORCEMENT_HISTORY`: determination exists — informational;
- `COURT_DECISION_VARIES_ODPC`: court altered/set aside administrative outcome;
- `SOURCE_STALE`: source older than configured freshness threshold.

Forbidden automatic labels include "illegal", "unlicensed", "unregistered" or "non-compliant" based only on entity reconciliation.

## CRB evidence rule

`regulatory_crb_status` and `subject_specific_submission_status` are independent. A DCP's absence from a public approved-third-party list cannot prove that it does not furnish credit information.

Subject-specific submission claims require evidence such as the user's bureau report/history or another authorized source.

## Court/enforcement rule

Store the ODPC determination and later court proceeding separately. Do not overwrite the regulator outcome when a court later sets it aside or varies it; expose the current procedural effect instead.
