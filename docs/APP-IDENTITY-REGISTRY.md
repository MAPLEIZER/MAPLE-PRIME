# Kenya Loan App Identity Registry

## Purpose

The App Identity Registry is a public-evidence layer for mapping Android loan/credit applications used in Kenya to the legal entities that appear to operate, publish, support or own them.

The immediate problem is that an app's consumer-facing name, Play developer name and regulated legal entity name may all differ. KDR therefore does **not** store a single unqualified `owner` field. It preserves what was publicly observed and keeps ownership as a separately reviewable conclusion.

```text
Google Play app/package observation
        ≠
Play developer/support identity
        ≠
matching email/domain/name signal
        ≠
confirmed legal owner/operator
        ≠
CBK/ODPC/CRB regulatory status
```

## Data layers

### `marketplace_apps`

Stable app identity. An Android app is keyed by `store + package_name`, not by its display name. Display names can change while the package remains the same.

Current fields include first/last observed time and a conservative loan-relevance state.

### `app_store_observations`

Append-only public marketplace observations. Every import records the source provider, source URL and observation time together with the public fields that were visible at that point:

- package ID;
- app/display name;
- developer/publisher name and ID where published;
- public support email;
- developer website/domain;
- privacy-policy URL;
- Play listing URL;
- category and install-count text where supplied by the collector.

New observations do not overwrite previous observations. This lets KDR show later that an app changed developer name, contact address, domain or privacy-policy location.

### `app_ownership_links`

Evidence-scored links from an app to an existing KDR `Institution`. A link begins as `candidate` and requires explicit human review to become `confirmed` or `rejected`.

Current evidence signals include exact matches between:

- institution website domain and Play developer website domain;
- institution website domain and a corporate support-email domain;
- Play developer name and legal/trading name;
- app name and trading name.

A confidence score ranks review priority. It is **not** a probability of legal ownership and is never an automatic legal conclusion.

## Public support email rules

KDR may store a support/business email when it was publicly presented as app/developer contact information by the source being imported. Exact email search is then useful for finding all apps in the local KDR dataset that have used that address.

The domain after `@` is indexed for reverse lookup. Common public mailbox providers such as Gmail, Yahoo, Outlook, Hotmail, iCloud and Proton are deliberately excluded as *corporate-domain ownership signals*. For example, two apps using `something@gmail.com` do not become evidence that they share a legal owner merely because the domain is `gmail.com`.

## Reverse lookup

The dashboard supports:

```text
email  -> every observed app using that exact public support email
domain -> every observed app using that support/developer domain
app    -> candidate/confirmed/rejected institution links
```

Reverse lookup works against KDR's collected observations. Google Play does not need to support reverse-email search for this feature once KDR has built its own index.

## Data acquisition

KDR core does not depend on one commercial Google Play data provider. The ingestion contract is provider-neutral so public metadata exported from an external collector can be retained with its provenance.

Possible collector classes include:

- a locally operated Play metadata collector;
- a Google Play scraper/export service;
- a SERP/app-data API;
- an app-intelligence dataset.

KDR does not include CAPTCHA bypass, anti-bot circumvention or unattended proxy-rotation logic. Collection must comply with the chosen source/provider's access terms and controls.

### Normalize an export

`tools/playstore-import/normalize_export.py` accepts JSON and maps common field names such as `appId`, `title`, `developer`, `developerEmail`, `developerWebsite`, `privacyPolicy`, `url`, `genre` and `installs`.

Example:

```bash
python tools/playstore-import/normalize_export.py play-export.json \
  --source-provider apify \
  --source-url https://example.invalid/replace-with-real-export-run-url \
  > kdr-play-import.json
```

For a collector that gives no durable export/run URL, omit `--source-url`; KDR will preserve each Play listing URL as the observation source URL.

Then open **Loan apps -> Import normalized JSON** in the local dashboard. The browser reads the local file and sends at most 500 records to the local KDR API using the explicit `import_apps` local-action boundary.

The API contract is also available directly:

```text
POST /api/v1/apps/import/play
X-KDR-Local-Action: import_apps
```

## Building the first Kenya dataset

A practical first pass is:

1. Start from the current CBK DCP institutions already imported by KDR.
2. Use legal names, trading names and known corporate domains as collector search seeds.
3. Add Kenya-focused Play search terms such as digital loan, mobile loan, instant loan, cash loan and credit.
4. Normalize all results into KDR rather than deciding ownership inside the scraper.
5. De-duplicate by Play package ID.
6. Reverse-index public support emails/domains.
7. Generate candidate institution links.
8. Review high-confidence candidates manually, with the Play listing and observation source visible beside the evidence.
9. Keep unmatched apps public as `unresolved`/candidate identities instead of silently dropping them. These are often the most useful records for later investigation.
10. Re-run collection periodically so changed publisher/contact metadata becomes a new observation rather than destroying the old evidence.

A future scheduled collector can automate steps 2-6 while preserving the same ingestion contract.

## Reverse WHOIS

Reverse-WHOIS data is **not** a default ownership signal in this first phase. Modern WHOIS records are frequently privacy-protected, historical datasets can be stale, shared administrative contacts create false relationships, and an email appearing in domain-registration history does not by itself prove ownership of a loan app or lender.

If added later it should be a separately sourced evidence observation with provider, lookup time and historical/current status, not an automatic ownership confirmation.

# Future: loan cost / interest-rate history

Do not add mutable `interest_rate` fields to `marketplace_apps` or `institutions`. Loan pricing changes and often includes fees that make a simple nominal rate misleading.

The planned model is an append-only `loan_term_observations` layer containing, where evidence supports it:

- app/provider link;
- product/loan type;
- principal amount or amount band;
- quoted rate and rate basis (daily/weekly/monthly/annual);
- term/tenure;
- processing/service/platform fees;
- insurance/other mandatory charges;
- late/default charges where publicly disclosed;
- total repayment for a representative amount where derivable;
- calculated effective cost metrics with the calculation version recorded;
- currency;
- effective/observed dates;
- source URL and immutable source evidence reference;
- verification state.

This makes it possible to show **pricing history** instead of one easily manipulated current number.

# Future: provider ranking

Ranking must be transparent and decomposable rather than a black-box score. Candidate dimensions include:

- verified borrowing cost for comparable scenarios;
- disclosure/transparency completeness;
- complaint/review evidence quality;
- data-rights responsiveness where directly observed;
- regulatory-source status shown as factual context rather than a popularity score;
- product reliability/usability signals;
- peer-review aggregate with sample size and confidence interval.

A ranking should always expose its component scores, observation period, missing-data penalty and methodology version. A provider with little evidence must not rank highly merely because it has no recorded complaints.

# Future: peer review

Peer reviews should be separate from regulator evidence and ownership facts. Planned safeguards include:

- one review identity/account cannot freely mass-rate the same provider;
- rate limits and duplicate/spam detection;
- structured dimensions plus optional text;
- report/flag and moderation state;
- disclosed whether the reviewer says they actually borrowed from the provider;
- no requirement to publish sensitive loan/account identifiers;
- abuse-resistant aggregation (minimum sample sizes, Bayesian/weighted averages or equivalent);
- visible review count and distribution rather than only a single star value;
- right-of-reply/moderation workflow for providers without allowing them to erase legitimate criticism;
- immutable moderation/audit history for ranking-impacting changes.

Reviews must never alter the CBK/ODPC/CRB source record or turn an unverified ownership candidate into a confirmed link.
