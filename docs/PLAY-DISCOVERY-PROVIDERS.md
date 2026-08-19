# Google Play discovery providers

KDR's app-discovery pipeline is provider-neutral after metadata normalization. The alpha supports two indexed Google Play providers plus a bounded public-HTML fallback.

## Research console vs legacy discovery

The Evidence page now exposes two complementary workflows:

- **Google Play research console** — large enumeration runs with Finance-category crawling, custom keyword sweeps, pagination, dedupe, email-reuse flags and CSV export.
- **Legacy CBK-seeded discovery** — intentionally small searches around CBK identities for fast ownership-oriented checks.

The research console can request up to 25 provider search pages/requests, retain up to 500 unique app identities and optionally spend up to 100 SerpApi product-detail requests on developer-contact enrichment. Existing package IDs are skipped from re-ingest/re-enrichment by default, while reused support emails are flagged rather than treated as new evidence.

## Research modes

### Finance category crawl

For SerpApi.com, KDR starts with a category-only request:

```text
engine=google_play
store=apps
apps_category=FINANCE
gl=ke
hl=en
```

When SerpApi returns `serpapi_pagination.next_page_token`, KDR follows subsequent category pages until the configured page/request budget or unique-app limit is reached.

This is a crawl of Google's discoverable/ranked Finance surface. KDR does **not** label it a guaranteed exhaustive registry of every Finance app ever published because the upstream category surface and ranking are controlled by Google/the provider.

### Query sweep

Researchers can provide up to 20 comma/newline-separated search terms. Suggested terms include:

```text
loan
credit
mkopo
advance
salary advance
cash loan
mobile loan
quick loan
emergency loan
digital credit
microloan
borrow
pesa
```

Each unique term is searched independently, so keyword discovery is not limited to the old fixed `loan` bootstrap.

### Hybrid

Hybrid mode combines Finance-category browsing with the configured keyword terms. SerpApi pagination continuations are interleaved with the other queued search streams so one term does not consume the entire request budget before the others receive a first pass.

## Dedupe and enrichment semantics

KDR deduplicates discovery rows by Google Play package ID before ingest. The research result reports:

- unique packages discovered;
- package hits suppressed as duplicates across pages/queries;
- apps new to KDR;
- apps already present in the local registry;
- existing apps skipped from re-ingest when **Skip apps already in KDR** is enabled;
- support emails found;
- unique new support emails;
- support emails already present in KDR;
- new support emails repeated by multiple apps in the same run.

A repeated support email is **not** used to discard a distinct app: multiple apps can legitimately share one developer/support mailbox. Instead the UI marks the email as reused so a researcher does not treat it as a new contact lead.

SerpApi product-detail enrichment is optional. Setting the enrichment budget to `0` performs cheap app enumeration only; increasing it spends additional provider calls on new/not-skipped packages to collect richer contact metadata such as support email, website and privacy-policy URL when available.

Large research passes leave CBK ownership matching disabled by default. Researchers can enable it for a run, or reconcile promising apps after enumeration, avoiding an expensive institution-by-app matching loop during simple market mapping.

## Runtime provider selection

The research console can select `auto`, `serpapi` or `talordata` per run without exposing provider credentials to the browser. The provider keys remain in the local runtime environment.

## `auto` (default)

`KDR_PLAY_DISCOVERY_PROVIDER=auto` selects providers in this order for the legacy workflow:

1. TalorData when `KDR_TALORDATA_API_KEY` is configured;
2. SerpApi.com when `KDR_SERPAPI_API_KEY` is configured;
3. bounded public Google Play HTML collection.

The credentials remain separate because TalorData and SerpApi.com are different services with different endpoints and authentication schemes.

## `talordata`

TalorData uses its SERP API token with a Bearer-authenticated POST request. KDR's default endpoint is:

```text
https://api.talordata.com/accounts/v1/serp/get_serp_data
```

Configure the packaged install in `.kdr/runtime.env`:

```dotenv
KDR_PLAY_DISCOVERY_PROVIDER=talordata
KDR_TALORDATA_API_KEY=YOUR_TALORDATA_SERP_TOKEN
```

If your TalorData account exposes a different SERP endpoint, it can be overridden locally:

```dotenv
KDR_TALORDATA_SERP_ENDPOINT=https://your-account-endpoint.example/path
```

The research console can issue a Finance-category request and custom keyword requests through the TalorData adapter. KDR currently does not claim TalorData category pagination unless the provider contract exposes a supported continuation shape; SerpApi.com is the current indexed provider used for explicit multi-page category crawling.

TalorData API tokens must never be copied into KDR evidence URLs, exported datasets or diagnostic logs.

## `serpapi`

SerpApi.com exposes structured Google Play query, category, pagination and product endpoints. SerpApi documents keyword search (`q`) and category search (`apps_category`) as distinct Google Play search modes, so KDR deliberately does not combine them in one request.

Keyword example:

```text
engine=google_play
store=apps
q=mkopo
gl=ke
hl=en
```

Finance category example:

```text
engine=google_play
store=apps
apps_category=FINANCE
gl=ke
hl=en
```

Product details use `engine=google_play_product`, `store=apps`, and `product_id=<package>` so KDR can normalize developer identity, website, support email, privacy-policy URL and other public contact metadata returned by SerpApi.com.

Configure `.kdr/runtime.env`:

```dotenv
KDR_PLAY_DISCOVERY_PROVIDER=serpapi
KDR_SERPAPI_API_KEY=YOUR_SERPAPI_KEY
```

SerpApi.com's Account API health check is used for account diagnostics. It verifies account state and remaining searches without persisting or displaying the key.

## Switching providers

Both provider credentials may coexist in the local runtime file. The research console can choose either indexed provider for a specific run. The legacy collector continues to honor `KDR_PLAY_DISCOVERY_PROVIDER`.

Examples:

```dotenv
KDR_PLAY_DISCOVERY_PROVIDER=talordata
KDR_TALORDATA_API_KEY=...
KDR_SERPAPI_API_KEY=...
```

or:

```dotenv
KDR_PLAY_DISCOVERY_PROVIDER=serpapi
KDR_TALORDATA_API_KEY=...
KDR_SERPAPI_API_KEY=...
```

After changing the runtime file, choose **Repair / rebuild** in the installer so Docker Compose receives the new environment.

## `public_html` fallback

This mode makes bounded HTTPS requests directly to public `play.google.com` search/detail pages. KDR does not solve CAPTCHAs, rotate proxies or bypass Google anti-bot controls. HTTP 403/429 responses are recorded as bounded discovery failures. The large research console requires one of the indexed providers; the public-HTML mode remains available through the small legacy discovery path.

## Alternative index: 42matters

42matters exposes an indexed Android app Search API, package Lookup API, domain-search endpoint, privacy-policy/website metadata and, on higher plans, developer email. It remains a candidate for a later redundancy adapter; the alpha does not yet send requests to 42matters.
