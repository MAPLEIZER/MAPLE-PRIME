# Threat Model

## Assets

Highest sensitivity:

- legal name, phone, email, address, DOB;
- national-ID/passport information if ever supplied;
- credit reports and lender relationships;
- SMTP/OAuth/IMAP credentials/tokens;
- request/evidence attachments;
- encryption keys;
- hosted admin credentials.

Public regulatory snapshots are lower sensitivity but require integrity/provenance protection.

## Adversaries

- opportunistic internet attacker against hosted deployment;
- malicious/compromised dependency;
- malicious third-party website loaded by Playwright;
- malicious inbound email/attachment;
- compromised maintainer/release pipeline;
- curious or compromised hosted administrator;
- another tenant attempting IDOR/horizontal access;
- spam/abuse user trying to weaponize request automation.

## Principal threats and controls

| Threat | Control baseline |
|---|---|
| Database theft exposes PII | application-level encryption + separate keys |
| Backup theft | encrypted backups; key separation |
| Browser worker compromise | isolated worker; narrow job payload; no master key |
| Malicious email HTML/attachment | sanitize; size/type limits; malware scanning in hosted mode |
| SSRF through source/provider URLs | allowlisted source manifest; provider adapter policy |
| XSS from institution/case/email content | output encoding; sanitize rendered HTML |
| CSRF in hosted mode | same-site cookies/tokens; origin checks |
| IDOR/tenant escape | user-scoped queries + authorization checks + tests |
| Credential leakage in logs | structured redaction; no body logging |
| Mass spam | per-user workflow constraints, rate limits, explicit approval, deduplication |
| Wrong entity targeted | canonical matching confidence + manual review |
| False regulatory accusation | conservative discrepancy taxonomy + provenance |
| Supply-chain compromise | lockfiles, SBOM, dependency review, signed releases |
| Secret in Git | secret scanning + `.gitignore` + contributor rules |

## Data minimization

- regulatory explorer works without user identity data;
- collect only fields required for the chosen request;
- avoid ID documents until an institution specifically requires verification;
- where ID evidence is needed, prefer temporary encrypted upload, transmission, hash/audit record, then deletion;
- screenshots disabled by default;
- raw mail/evidence retention configurable and minimized.

## Hosted authorization model

- normal user can access only own identity, requests and evidence;
- regulatory data is shared/read-only;
- support/admin access requires explicit audited break-glass path;
- no hidden "view all user evidence" dashboard;
- privileged actions require MFA before public pilot.

## Abuse resistance

The system is for legitimate data-subject requests. It should block or review:

- repeated duplicate submissions to the same institution;
- campaigns targeting institutions with no claimed relationship/context where the workflow requires one;
- request templates containing threats/harassment;
- attempts to use browser workers as arbitrary URL fetchers;
- automated CAPTCHA bypass unless explicitly configured and lawful.

## Security release gate

No public hosted service until the ROADMAP go/no-go checklist passes and an independent review tests encryption, authorization, browser isolation, backups, input handling and secrets management.
