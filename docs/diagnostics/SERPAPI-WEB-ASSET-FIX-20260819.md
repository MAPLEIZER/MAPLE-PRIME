# SerpApi discovery and web asset diagnostic — 2026-08-19

## Evidence from the support bundle

The post-update support bundle showed that the dashboard itself was healthy, but both web brand assets returned HTTP 404 from the Nginx container:

- `/kdr-app-icon.png?v=20260819b`
- `/kdr-logo-transparent.png?v=20260819b`

The source files existed under `apps/web/public`, but the web Dockerfile copied only `src` into the Vite build stage. Vite therefore never received the `public` directory when the container image was built.

The same bundle showed successful HTTP 200 responses from the Play discovery endpoint but no apps in the registry afterward. The indexed-provider implementation was searching only a small rotating set of CBK legal/trading-name terms. This is too low-recall for apps whose Play brand differs from the regulator legal name.

## SerpApi playground evidence supplied by the project owner

A Google Play search configured as:

- engine: `google_play`
- query: `loan`
- app category: `FINANCE`
- country: `ke`
- language: `en`

returned a high-signal set of Kenyan lending apps and publishers, including Branch, Tala, Zash, FlashPesa, Fiza, LendPlus, Zenka, DG Loan and others.

## Fix

SerpApi discovery now starts each bounded run with the high-recall Kenya Finance `loan` query, then uses regulator identity terms only as enrichment if the broad result set did not fill the run limit. Provider-specific SerpApi searches use the same `FINANCE`, `ke`, and `en` scope.

The web Dockerfile now copies `public` into the Vite build stage. Container CI also requests both public brand asset URLs and fails if either is not served successfully.

The API key remains runtime-only and is not written to evidence or source URLs.
