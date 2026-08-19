# Google Play discovery providers

KDR's app-discovery pipeline is provider-neutral after metadata normalization. The alpha supports two Google Play collection modes.

## `auto` (default)

`KDR_PLAY_DISCOVERY_PROVIDER=auto` selects SerpApi when `KDR_SERPAPI_API_KEY` is configured. Otherwise KDR uses the bounded public Google Play HTML collector.

## `serpapi` (recommended for alpha data collection)

SerpApi exposes structured Google Play search and product endpoints. KDR uses:

- `engine=google_play`, `store=apps`, `gl=ke`, `hl=en` for CBK-seeded app search;
- `engine=google_play_product`, `store=apps`, `product_id=<package>` for app metadata;
- developer contact fields such as developer name, website, support email and privacy-policy URL when the provider returns them.

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

Interactive dashboard runs default to 5 CBK identities and 15 app details to protect local responsiveness. The optional Docker `discovery` profile can use larger rotating batches for dataset collection.
