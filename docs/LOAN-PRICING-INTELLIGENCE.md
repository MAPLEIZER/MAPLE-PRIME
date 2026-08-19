# Loan Pricing Intelligence

## Purpose

KDR's pricing layer records evidence about the actual cost of a loan offer without reducing the offer to a single advertised interest-rate field.

The core comparison is:

```text
amount actually received
        ↓
total amount required for baseline repayment
        ↓
effective cost over the observed term
        ↓
known interest + mandatory fee components
        ↓
any unexplained cost gap
```

This is deliberately separate from app ownership, regulatory status, provider ranking and peer review.

## Current implementation

Stage 2 is implemented as an append-only `loan_term_observations` ledger introduced by Alembic revision `0005_loan_pricing`.

Each observation is tied to a tracked marketplace app and may optionally reference a KDR institution when that attribution is explicitly supplied. KDR does **not** infer the institution from an unreviewed app-ownership candidate when a pricing observation is recorded.

Current fields include:

- app ID;
- optional institution ID;
- source type/provider/URL;
- timezone-aware observation time;
- currency;
- amount actually received;
- total baseline repayment;
- term in days;
- advertised interest rate and its stated basis where available;
- interest amount;
- processing, service, insurance, disbursement and other mandatory fees;
- separately disclosed late/default charge;
- separately disclosed rollover/extension charge;
- calculated effective cost amount;
- calculated effective period-cost percentage;
- calculated known-cost amount;
- calculated unexplained-cost amount;
- canonical source payload and SHA-256 observation hash.

Identical evidence payloads are de-duplicated by hash. A later observation with changed terms remains a new row, preserving pricing history.

## Calculation methodology v1

For one observed loan scenario:

```text
effective_cost_amount = total_repayment - amount_received

effective_cost_percent =
    effective_cost_amount / amount_received × 100

known_cost_amount =
    interest_amount
    + processing_fee
    + service_fee
    + insurance_fee
    + disbursement_fee
    + other_mandatory_fees

unexplained_cost_amount =
    max(effective_cost_amount - known_cost_amount, 0)
```

Example:

```text
Amount received:          KES 5,000
Total repayment:          KES 6,050
Observed term:            30 days
Interest amount:          KES   500
Processing fee:           KES   250
Service fee:              KES   200
Insurance fee:            KES   100

Effective cost amount:    KES 1,050
Effective period cost:          21%
Known cost amount:        KES 1,050
Unexplained cost:         KES     0
```

The effective percentage is a cost percentage for the **observed term**. It is **not APR**. KDR does not currently annualize short-term offers because a simple annualization can create a misleading comparison unless the compounding, renewal and legal disclosure methodology is explicitly versioned.

## Consistency rules

The API rejects observations where:

- amount received is not positive;
- total repayment is below amount received;
- known interest plus mandatory fee components exceed the observed repayment cost beyond the small rounding tolerance;
- an optional public source URL is not HTTPS;
- observation time has no timezone;
- term is outside the supported positive range.

A repayment cost that is **greater** than the known line items is allowed, but the difference is surfaced as `unexplained_cost_amount` instead of being silently assigned to interest.

## Late, default and rollover charges

`disclosed_late_fee` and `disclosed_rollover_fee` are kept separately from baseline mandatory charges.

They do not silently increase the baseline effective-cost calculation unless a collected scenario's `total_repayment` itself already represents a repayment state where those charges apply.

This distinction is important for products that advertise a modest nominal rate but monetize extensions, rollovers or delinquency separately.

## Evidence provenance

Every observation records:

```text
source_type
source_provider
source_url (where available)
observed_at
canonical payload
SHA-256 observation hash
```

Supported source classes currently include:

- `public_disclosure`;
- `marketplace_listing`;
- `borrower_report`;
- `manual_test`;
- `regulator_publication`.

The dashboard's current manual entry flow uses `public_disclosure`. Other source classes are API-ready for later collectors and review workflows.

Borrower-reported data must not require public account numbers, national identifiers, raw private messages or other unnecessary sensitive identifiers.

## API

Read pricing history:

```text
GET /api/v1/pricing
GET /api/v1/pricing?app_id=<app-id>
GET /api/v1/pricing?institution_id=<institution-id>
```

Summary:

```text
GET /api/v1/pricing/summary
```

Public export:

```text
GET /api/v1/pricing/export
schema_version = kdr-loan-pricing-v1
```

Record an observation locally:

```text
POST /api/v1/pricing
X-KDR-Local-Action: record_pricing
Content-Type: application/json
```

The explicit local-action header prevents an ordinary cross-surface request from being mistaken for an intentional evidence mutation.

## Dashboard

The **Pricing** dashboard surface provides:

- app selection;
- append-only pricing history;
- amount received and total repayment;
- effective period cost;
- advertised rate/basis where disclosed;
- known fee composition;
- unexplained-cost visibility;
- separately disclosed late and rollover/extension charges;
- observation date and source provenance;
- structured local entry for a new public pricing observation.

The UI explicitly states that the period-cost metric is **not APR** and is **not a provider ranking**.

## What Stage 2 does not claim

A pricing observation is evidence for a specific scenario and date. It does not by itself prove that:

- every borrower received the same quote;
- the lender always charges those terms;
- an optional institution link is legally conclusive ownership;
- the offer complies or fails to comply with Kenyan law;
- the provider is better or worse than another provider overall.

Those questions require additional evidence and separate methodologies.

## Next pricing extensions

Useful additions before provider ranking include:

1. product/loan-type identity and amount bands;
2. explicit evidence-review state for pricing observations;
3. immutable source-snapshot references where KDR captured the original bytes;
4. effective-from/effective-to dates where a provider publishes them;
5. comparable-scenario selection, for example KES 5,000 over 30 days;
6. discrepancy detection between advertised/public terms and sufficiently supported borrower reports;
7. methodology-version storage on derived calculations;
8. historical charts only after comparable-scenario rules are enforced.

Provider ranking remains a later layer. It must consume reviewed pricing evidence rather than mutate or reinterpret the raw observation ledger.
