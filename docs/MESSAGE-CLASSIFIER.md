# KDR loan-message classification engine

KDR uses a staged, privacy-first model strategy.

## Stage 1 — phone rule baseline

The Android app extracts a fixed `kdr-msg-v1` feature vector and classifies locally. Features include message length/ratios, bounded keyword-family counts, amount/URL/phone counts, sender shape and 64 hashed token buckets. Raw text is not part of the feature object.

Current classes:

- `non_loan`
- `loan_marketing`
- `loan_application`
- `loan_approval`
- `loan_disbursement`
- `loan_repayment_reminder`
- `loan_overdue_collection`
- `crb_notice`
- `loan_other`

This baseline is intentionally small enough for Android 6.0-era devices and requires no ML runtime.

## Stage 2 — self-hosted learning

After pairing, the user may explicitly send **derived features only** to their own KDR server. The server hashes the client identifier before persistence. Upload is disabled until the desktop installer enables mobile telemetry with a generated bearer token, and Android upload still requires a visible button press.

The server stores the phone prediction separately from a later explicit `user_label`. Only records with a user label are eligible for model training. Rule-engine predictions never become training truth automatically.

## Stage 3 — optional XGBoost experiment

XGBoost is an optional server-side dependency, not part of the normal API image or Android APK. Install an ML development environment and run:

```bash
cd apps/api
pip install -e '.[ml]'
python -m app.ml.train_xgboost --output ../../local-data/models
```

Training refuses to run with fewer than 50 explicitly labeled rows or fewer than two classes. It produces an XGBoost JSON model plus a manifest containing the exact `kdr-msg-v1` feature order and class mapping.

XGBoost's JSON model format is used for server experimentation. KDR does **not** attempt to embed the full XGBoost runtime on API-23 phones. If a learned model materially improves the rule baseline, a later step can distill it into a compact linear/tree representation for on-device inference after parity/security tests.

## Model promotion rules

A trained model should not replace the baseline merely because training accuracy is high. Promotion should require held-out evaluation, per-class precision/recall, false-positive review, versioned model manifests, rollback support, and a privacy review verifying that the training set contains no raw communications.
