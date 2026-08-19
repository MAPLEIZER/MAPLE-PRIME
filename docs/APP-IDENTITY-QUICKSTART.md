# App Identity Registry — first Kenya dataset

This is the shortest path from the existing KDR CBK source sync to a reviewable public loan-app dataset.

## 1. Update KDR and sync CBK

After the App Identity Registry migration is installed, run the normal regulator sync. The CBK portion now materializes canonical `digital_credit_provider` institutions from the regulator observations and backfills the observation-to-institution links even when the PDF snapshot was already present.

The immutable CBK source payload remains separate from the current institution index.

## 2. Export collector search seeds

Open:

```text
GET /api/v1/apps/discovery/seeds
```

The response is tied to the latest CBK DCP snapshot and contains, per CBK record:

- legal name;
- trading name where published;
- official website/domain where published;
- publicly listed CBK contact emails;
- convenience `search_terms` for an external Play collector;
- source observation ID.

These are discovery inputs, not proof that every search result belongs to the DCP.

## 3. Collect public Play metadata

Use a collector of your choice. KDR deliberately does not hard-depend on Apify, SerpApi, DataForSEO, 42matters or a particular scraper implementation.

Useful collection strategies include:

- search by CBK legal name;
- search by CBK trading name;
- query/search by known corporate domain where the provider supports it;
- use the published CBK email as a reverse lookup where an app-intelligence dataset supports that operation;
- supplement with Kenya/finance search terms to find apps that do not obviously disclose their regulated identity.

Do not make the collector decide legal ownership. Return the public marketplace fields to KDR and let the evidence/review layer handle attribution.

## 4. Normalize the export

```bash
python tools/playstore-import/normalize_export.py play-export.json \
  --source-provider YOUR_COLLECTOR_NAME \
  --source-url https://YOUR-DURABLE-EXPORT-OR-RUN-URL \
  > kdr-play-import.json
```

The normalizer handles common field names including:

```text
appId / packageName
title / appName
developer / developerName
developerEmail / supportEmail
developerWebsite
privacyPolicy
url / playUrl
genre / category
installs
```

It fails if a stable Android package identity is unavailable.

## 5. Import into KDR

Dashboard:

```text
Loan apps -> Import normalized JSON
```

or API:

```http
POST /api/v1/apps/import/play
X-KDR-Local-Action: import_apps
Content-Type: application/json
```

Imports are capped at 500 records per request. App identity is de-duplicated by store + package ID while marketplace observations remain append-only.

## 6. Review ownership evidence

KDR currently scores evidence such as:

```text
CBK-published support email == Play public support email      strong
institution website domain == Play developer website domain  strong
institution domain == Play support-email corporate domain    supporting
institution domain == privacy-policy domain                  supporting
CBK legal/trading name == Play developer name                supporting
trading name == app display name                             supporting
```

Common mailbox domains such as Gmail, Yahoo, Outlook, Hotmail, iCloud and Proton are not treated as corporate-domain evidence. An **exact** email address that is explicitly published by CBK can still be useful evidence even when its domain is generic.

Every generated link remains:

```text
candidate
```

until a local reviewer explicitly chooses Confirm or Reject.

## 7. Reverse search the local database

```text
GET /api/v1/apps?email=support@example.co.ke
GET /api/v1/apps?domain=example.co.ke
GET /api/v1/apps?q=example
```

Once KDR has accumulated marketplace observations, this becomes the reverse-email/domain database that Google Play itself does not expose as a normal public search function.

## 8. Publish a safe registry export

```text
GET /api/v1/apps/export
```

The `kdr-app-registry-v1` export includes the latest public marketplace observation and provenance for each tracked package. Confirmed and clearly-labelled candidate ownership links are included. Rejected ownership hypotheses are omitted from the public export so downstream consumers do not mistake a rejected association for a current relationship.

## 9. Re-run collection over time

Periodic imports create new observations instead of overwriting history. This is how KDR can later show that an app changed:

- display name;
- Play developer/publisher identity;
- public support email;
- developer domain;
- privacy-policy URL;
- store visibility/metadata captured by a sufficiently complete collector.

A partial keyword search must **not** be used to declare an app delisted. A future complete collection-run model should record search scope/completeness before absence can be interpreted as marketplace removal.

## Next data layer

Do not put a single mutable `interest_rate` field on the app. The next phase should add append-only loan-term observations with amount, tenure, rate basis, fees, total repayment, source/effective dates and calculation methodology. Provider rankings and peer reviews should be separate derived layers so public opinion can never rewrite ownership or regulator facts.
