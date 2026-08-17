# ADR 0002: Greenfield core with upstream reference implementations

**Status:** Accepted

## Decision

Build a Kenya-first greenfield core while borrowing compatible patterns only after file-level licence/provenance review from projects such as Symaira EraseMe, auto-identity-remove, Eraser, Visible Data Broker Remover and JustDeleteMe.

## Rationale

The researched upstream projects contain useful pieces but encode different jurisdictions, data-broker ontologies and maturity/security assumptions. A direct fork would require removing enough core assumptions that provenance and architecture would become harder to reason about.

Apache-2.0 is used for the new core. Any copied upstream code must retain its required notices and licence terms.
