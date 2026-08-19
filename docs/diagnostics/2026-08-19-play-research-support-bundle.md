# Play research support-bundle regression — 2026-08-19

Observed in support bundle `KDR-support-20260819-203746Z.zip` from source SHA `fdb08e32becab70241e0af1a62a9ec55f65db277`.

## Confirmed failures

1. A long `POST /api/v1/apps/discovery/research` exceeded the research-specific Nginx `proxy_read_timeout 300s` and returned HTTP 504.
2. A later research run reached `AppRegistryRepository.ingest_play()` and failed while updating an existing SQLite row because SQLite returned `first_seen_at` / `last_seen_at` as offset-naive datetimes while the incoming Play observation was UTC-aware:

```text
TypeError: can't compare offset-naive and offset-aware datetimes
```

## Remediation contract

- Normalize marketplace timestamps at the SQLAlchemy type boundary so SQLite-loaded app and observation timestamps are always aware UTC datetimes.
- Add a regression test that commits/expires an app row through SQLite and then re-ingests a later aware observation.
- Increase only the explicit operator research route's proxy window; unrelated API routes keep the shorter default timeout.
- Keep large research bounded by the existing page/app/enrichment limits.
