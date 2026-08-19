# Legal AI readiness rules

A future KDR legal assistant should use retrieval/citation, not free-form legal guessing.

## Minimum answer contract

Every material legal answer should return:

- issue/question detected;
- relevant Kenyan source(s);
- exact provision or source segment where available;
- source version/date;
- facts supplied by the user versus inferred facts;
- uncertainty and missing evidence;
- possible next steps;
- a clear statement that educational guidance is not legal advice.

## Prohibited shortcuts

The model must not turn a message classification into a legal finding, infer ODPC non-registration from a missing search result, infer CRB submission from a public-provider list, or convert an ODPC administrative determination into a final court finding.

Raw private communications should remain outside a hosted AI prompt by default. Prefer on-device feature extraction, user-selected excerpts, or explicit one-off consent for any future raw-text analysis mode.
