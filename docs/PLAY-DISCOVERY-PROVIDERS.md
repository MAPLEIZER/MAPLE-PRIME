# Google Play discovery providers

KDR's app-discovery pipeline is provider-neutral after metadata normalization. The alpha supports two indexed Google Play providers plus a bounded public-HTML fallback.

## `auto` (default)

`KDR_PLAY_DISCOVERY_PROVIDER=auto` selects providers in this order:

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

KDR sends Kenya/English Google Play discovery requests, starting with `loan` in the Finance category and then selected CBK trading/legal names until the bounded app limit is filled. Search results are normalized directly into KDR app evidence, so a second product-detail call is not required for an app to enter the registry.

TalorData API tokens must never be copied into KDR evidence URLs, exported datasets or diagnostic logs.

## `serpapi`

SerpApi.com exposes structured Google Play query, category and product endpoints. SerpApi documents keyword search (`q`) and category search (`apps_category`) as distinct Google Play search modes, so KDR deliberately does not combine them in one request.

The first keyword pass is:

```text
engine=google_play
store=apps
q=loan
gl=ke
hl=en
```

If that does not fill the bounded run, KDR performs a separate Finance category pass:

```text
engine=google_play
store=apps
apps_category=FINANCE
gl=ke
hl=en
```

Selected CBK trading/legal-name enrichment searches use the keyword mode. Product details use `engine=google_play_product`, `store=apps`, and `product_id=<package>` so KDR can normalize developer identity, website, support email, privacy-policy URL and other public contact metadata returned by SerpApi.com.

Configure `.kdr/runtime.env`:

```dotenv
KDR_PLAY_DISCOVERY_PROVIDER=serpapi
KDR_SERPAPI_API_KEY=YOUR_SERPAPI_KEY
```

SerpApi.com's Account API health check is used only when SerpApi.com is the active provider. It verifies account state and remaining searches without persisting or displaying the key.

## Switching providers

Both provider credentials may coexist in the local runtime file. Changing `KDR_PLAY_DISCOVERY_PROVIDER` switches the active collector without destroying the other saved credential.

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

This mode makes bounded HTTPS requests directly to public `play.google.com` search/detail pages. KDR does not solve CAPTCHAs, rotate proxies or bypass Google anti-bot controls. HTTP 403/429 responses are recorded as bounded discovery failures.

## Alternative index: 42matters

42matters exposes an indexed Android app Search API, package Lookup API, domain-search endpoint, privacy-policy/website metadata and, on higher plans, developer email. It remains a candidate for a later redundancy adapter; the alpha does not yet send requests to 42matters.

## Batch sizing and evidence semantics

Interactive dashboard runs default to 5 CBK identities and 15 app identities to protect local responsiveness. Indexed-provider search rows are evidence in their own right and are retained even if optional enrichment fails or quota is exhausted. The optional Docker `discovery` profile can use larger rotating batches for dataset collection.
