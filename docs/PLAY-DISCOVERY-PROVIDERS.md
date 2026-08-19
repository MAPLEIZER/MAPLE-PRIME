# Google Play discovery providers

KDR's app-discovery pipeline is provider-neutral after metadata normalization. The alpha supports two Google Play collection modes.

## `auto` (default)

`KDR_PLAY_DISCOVERY_PROVIDER=auto` selects SerpApi when `KDR_SERPAPI_API_KEY` is configured. Otherwise KDR uses the bounded public Google Play HTML collector.

## `serpapi` (recommended for alpha data collection)

SerpApi exposes structured Google Play search and product endpoints. KDR now starts each bounded indexed-discovery run with a high-recall Kenya finance bootstrap:

```text
engine=google_play
store=apps
q=loan
apps_category=FINANCE
gl=ke
hl=en
```

That bootstrap intentionally mirrors the working Kenya/English/Finance search used in the SerpApi playground. It discovers branded loan apps even when their Play Store title or publisher does not closely resemble the CBK legal entity name.

If that market search does not fill the current app limit, KDR then searches selected CBK trading/legal names using the same `FINANCE`, `ke`, and `en` scope. Product details are collected with `engine=google_play_product`, `store=apps`, and `product_id=<package>` so KDR can normalize developer identity, website, support email, privacy-policy URL and other public contact metadata returned by SerpApi.

Configure the local packaged install in `.kdr/runtime.env`:

```dotenv
KDR_PLAY_DISCOVERY_PROVIDER=serpapi
KDR_SERPAPI_API_KEY=YOUR_PRIVATE_KEY
```

Then run **Repair / rebuild** in the installer. The Compose stack injects the values into the API and optional discovery worker. The secret is not copied into evidence/source URLs or application observations.

SerpApi is a third-party service. Its availability, pricing and output schema are outside KDR's control, so provider responses are normalized into KDR's own schema and remain evidence rather than regulatory truth.

## `public_html` fallback

This mode makes bounded HTTPS requests directly to public `play.google.com` search/detail pages. KDR does not solve CAPTCHAs, rotate proxies or bypass Google anti-bot controls. HTTP 403/429 responses are recorded as bounded discovery failures.

## Alternative index: 42matters

42matters exposes an indexed Android app Search API, package Lookup API, domain-search endpoint, privacy-policy/website metadata and, on higher plans, developer email. It is a strong candidate for a second adapter if KDR needs provider redundancy. The alpha does not yet send requests to 42matters.

## Batch sizing

Interactive dashboard runs default to 5 CBK identities and 15 app details to protect local responsiveness. With SerpApi, the broad Kenya Finance bootstrap runs first and provider-name searches are only used when the run still has capacity. The optional Docker `discovery` profile can use larger rotating batches for dataset collection.
