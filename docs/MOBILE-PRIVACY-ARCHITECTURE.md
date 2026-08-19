# Mobile Privacy Architecture

## Goal

Help a user identify which licensed digital credit provider (DCP) is behind an app, sender ID or contact channel without turning the mobile app into a surveillance or communications-harvesting product.

A lender may operate multiple apps or brands. The useful shared artifact is the **mapping** between an observed app/contact identifier and a regulated institution, together with provenance/confidence — not the user's private conversation history.

## Two separate data planes

### 1. Local observation plane

Data may be supplied by the user to the device for local matching. Examples:

- app package name;
- sender ID or manually selected phone number;
- lender/brand hint;
- content explicitly shared into KDR by the user for one-time local classification.

Raw communication content should be ephemeral and stay on-device. It must not enter analytics, crash reports or server logs.

### 2. Shared mapping plane

A separate explicit action contributes only the minimum mapping record needed to improve the community registry, for example:

```json
{
  "kind": "app_package",
  "institution_hint": "Example Credit",
  "app_package": "com.example.credit",
  "observed_at": "2026-08-18T06:00:00Z"
}
```

The server computes/deduplicates an evidence fingerprint and stores the contribution as **unverified**. It does not automatically link the evidence to an institution or treat it as a regulator fact.

## Data never accepted by the shared API

- raw SMS/message bodies;
- complete SMS inbox exports;
- unrestricted call-log history;
- call duration/history used for profiling;
- contact books/address books;
- call recordings;
- unrelated third-party phone numbers or names;
- authentication codes;
- financial account secrets.

The API uses strict `extra=forbid` validation so accidental extra fields fail rather than being silently stored.

## Android / Google Play boundary

Google Play treats SMS and Call Log permissions as restricted. The normal requirement is that an app is the relevant default handler, with limited approved exceptions. Google's published policy lists research based on SMS as an invalid use and states that using one user's restricted communications data to directly influence another user's product experience is disallowed.

Therefore the Play-distributed KDR application must not depend on `READ_SMS` or `READ_CALL_LOG` to crowdsource the DCP database.

Preferred flows are:

- manual paste/entry of a sender identifier;
- OS share intent into KDR for explicit one-item analysis;
- app/package selection where platform APIs legitimately expose it;
- local lookup against a downloaded signed mapping database;
- explicit contribution of the reduced mapping record only.

A research/sideload build must not be used as a mechanism to evade platform or Kenyan privacy requirements. Any privileged experimental build stays local-only unless separately reviewed.

## Kenyan data-protection position

KDR will not attempt to "circumvent" controller/processor status. Under the Data Protection (Registration of Data Controllers and Data Processors) Regulations, a party determining the purpose and means of processing is a controller; a processor processes on behalf of a controller under the relevant relationship/instructions.

The hosted project may have different roles for different data planes. For example, a future service could potentially process a user's private workflow data on the user's behalf while independently determining the purpose/means of the shared DCP mapping database. That second activity should be treated as potentially controller activity and reviewed accordingly.

Before accepting public contributions or other users' sensitive data, obtain Kenyan legal/privacy review and determine ODPC registration, notices, lawful basis, retention, data-subject rights, contracts and cross-border/cloud obligations based on the actual operating model.

## Consent and withdrawal

Contribution consent is separate from using the app. A user can use local matching without contributing data.

A future hosted contribution service must provide:

- clear purpose-specific notice before upload;
- an explicit contribution action;
- contribution provenance without publicly identifying the contributor;
- a deletion/withdrawal workflow where legally applicable;
- abuse/reporting mechanisms for incorrect mappings.

## Confidence model

Community mapping evidence starts as `unverified`.

A proposed institution mapping may progress through:

```text
unverified -> corroborated -> manually_verified -> regulator_or_provider_verified
                  \-> disputed -> rejected
```

No single user contribution should create a definitive public mapping when it could expose another person or misidentify an institution.

## Primary references

- Kenya Data Protection Act: https://new.kenyalaw.org/akn/ke/act/2019/24/eng@2022-12-31
- Data Protection (Registration of Data Controllers and Data Processors) Regulations: https://new.kenyalaw.org/akn/ke/act/ln/2021/265/eng@2022-12-31
- Google Play SMS and Call Log permissions policy: https://support.google.com/googleplay/android-developer/answer/10208820
