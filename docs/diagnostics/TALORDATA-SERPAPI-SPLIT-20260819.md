# TalorData / SerpApi.com provider split — 2026-08-19

## Diagnostic finding

The credential originally entered into `KDR_SERPAPI_API_KEY` came from the TalorData dashboard. TalorData and SerpApi.com are separate SERP providers with different authentication and request contracts, so a TalorData token cannot be validated against SerpApi.com's Account/Search endpoints.

A real SerpApi.com account was then configured successfully. Its Account API reported an active Free Plan with remaining quota, proving the SerpApi.com key itself was valid. Google Play discovery still returned HTTP 400.

The HTTP 400 was traced to request construction: KDR combined SerpApi.com's Google Play keyword-search parameter `q` with category-search parameter `apps_category`. SerpApi.com documents those as separate Google Play search modes.

## Fix

KDR now supports three explicit collection modes:

- `talordata` — Bearer-token POST requests to TalorData's SERP endpoint;
- `serpapi` — SerpApi.com query/category/product APIs and Account API health checks;
- `public_html` — bounded direct public Google Play HTML fallback without anti-bot bypass.

`auto` prefers TalorData when configured, then SerpApi.com, then public HTML.

SerpApi.com now performs `q=loan` and `apps_category=FINANCE` as separate requests. TalorData gets a dedicated adapter and credential variable (`KDR_TALORDATA_API_KEY`).

Both indexed-provider credentials may coexist locally so researchers can switch providers without re-entering secrets. Provider tokens are never copied into evidence URLs or exported app observations.
