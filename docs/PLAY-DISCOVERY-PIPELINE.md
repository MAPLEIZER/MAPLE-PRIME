# Google Play → CBK Discovery Pipeline

KDR alpha can now collect public Google Play metadata directly from regulator-derived discovery seeds.

## Pipeline

1. Read the latest persisted CBK DCP snapshot.
2. Build provider search terms from legal name, trading name and official domain.
3. Search public `play.google.com` pages scoped to Kenya.
4. Extract Android package IDs from search results.
5. Fetch bounded public detail pages.
6. Normalize app/developer identity, public support email, privacy-policy URL, category and install metadata when exposed.
7. Append the observation to the app identity registry.
8. Run the existing CBK/app evidence scorer.
9. Mirror resulting ownership candidates into the typed `operated_by` relationship graph with evidence records.

KDR does not log in, solve CAPTCHAs, rotate identities/proxies or bypass Google Play anti-bot controls. HTTP 403/429 responses are recorded as bounded failures and the run stops relying on that request.

## Manual run

```text
POST /api/v1/apps/discovery/run?max_providers=25&max_apps=100
X-KDR-Local-Action: discover_apps
```

## Scheduled worker

The Docker Compose `discovery` profile runs the same collector periodically. It is deliberately a profile so ordinary local alpha startup and CI do not unexpectedly scrape a third-party service.

```text
docker compose --profile discovery up -d
```

Defaults are one run per day, 25 CBK providers and at most 100 unique app detail pages per run. The provider window rotates by day so the alpha can accumulate observations without repeatedly hammering the first records in the CBK directory.

Public Play metadata is evidence, not ownership proof. Package IDs and historical observations remain stable even if branding, contact information or app names change.
