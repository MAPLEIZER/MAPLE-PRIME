# Chapter 7 — Triage a suspicious loan-app message

This chapter is a teaching workflow, not a breach detector.

## 1. Classify the message

KDR's lightweight classifier uses categories such as marketing, application/approval, disbursement, repayment reminder, overdue/collection, CRB notice and non-loan. The phone can derive features locally without uploading the message body.

## 2. Identify the sender/provider

Check sender ID, phone number, app package/trading name and known institution aliases. Treat crowd-sourced mappings as unverified until corroborated.

## 3. Ask legal questions

- Was the message intended for you?
- Does it reveal another person's loan/debt information?
- Is it marketing, and was an opt-out available?
- Is the provider using contact-list/third-party information?
- Is a CRB action claimed, and is there subject-specific evidence?
- Is the message threatening, deceptive or simply unwanted?

## 4. Preserve evidence safely

Keep dates, sender identifiers and screenshots locally. Avoid publishing third-party personal data. Raw SMS bodies should not become community telemetry by default.

## 5. Choose the next step

Possible actions include contacting the provider, exercising access/rectification/erasure/objection rights, disputing inaccurate CRB information, or preparing an ODPC complaint. KDR should show source-backed options and uncertainty.
