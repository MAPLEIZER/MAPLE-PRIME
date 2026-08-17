# Contributing

## Regulatory data PRs

Every regulatory-data change must identify:

- authority;
- source URL;
- retrieval date;
- publication/effective date where available;
- SHA-256/snapshot identifier;
- fields changed;
- entity-match evidence;
- any manual interpretation.

Do not put personal credit reports, identity documents, phone numbers, private emails or other user PII in issues or pull requests.

## Code changes

- keep regulator observations separate from conclusions;
- add tests for parsers/matching/state transitions;
- institution-specific automation belongs under `providers/kenya/`;
- never hard-code production credentials or user PII;
- preserve conservative UI/report language.

## Commit style

Prefer small scoped commits such as:

```text
add cbk dcp snapshot parser
add odpc reconciliation review queue
harden evidence attachment handling
```
