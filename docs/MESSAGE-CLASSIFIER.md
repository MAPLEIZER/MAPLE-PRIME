# KDR loan-message classification engine

KDR uses a staged, privacy-first classification strategy designed to remain useful on Android 6.0-era devices without shipping a large ML runtime.

## Stage 1 — on-device baseline

The Android app extracts a fixed `kdr-msg-v1` feature vector and classifies locally. Raw text is not part of the feature object.

The current 80-dimensional vector contains:

- message length, digit ratio and uppercase ratio;
- bounded keyword-family counts for loan, marketing, approval, disbursement, repayment, overdue/collection and CRB concepts;
- amount, URL and phone-number counts;
- sender-shape flags;
- 64 bounded hashed token buckets.

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

The baseline model is `rules-v1`. It requires no TensorFlow, PyTorch, ONNX or XGBoost runtime on the phone.

## Stage 2 — self-hosted learning loop

After pairing, the user can explicitly send **derived features only** to their own KDR server.

The server:

- rejects extra/raw-message fields at schema validation;
- hashes the Android client identifier before persistence;
- stores the phone prediction separately from the server prediction;
- stores an optional `user_label` separately from both predictions;
- keeps mobile telemetry disabled until the desktop installer explicitly enables it with a generated bearer token.

Android upload is never automatic. Scanning/classification and transmission are separate user actions.

### Human-label protection

Training labels are intentionally more restrictive than telemetry:

- a bulk SMS scan may send derived observations but cannot apply one human label to all of them;
- only **one explicitly shared message** can receive a human correction/confirmation in the Android UI;
- the selected label is sent only when the user presses **Send derived telemetry**;
- leaving the foreground clears the ephemeral observation and pending feedback state.

This reduces accidental dataset poisoning and prevents the rule engine from training a future model on its own guesses.

## Stage 3 — optional XGBoost experiment

XGBoost is an optional server-side development dependency, not part of the normal API image or Android APK.

Install an ML development environment and run:

```bash
cd apps/api
pip install -e '.[ml]'
python -m app.ml.train_xgboost --output ../../local-data/models
```

Training refuses to run with:

- fewer than 50 explicitly human-labeled rows; or
- fewer than two labeled classes.

The training pipeline uses only `user_label` rows. Phone/server predictions never become ground truth automatically.

Outputs:

```text
loan-message-xgboost.json
loan-message-xgboost.manifest.json
```

The manifest records:

- `kdr-msg-v1` feature schema;
- exact feature order;
- class mapping;
- training-row count;
- training timestamp;
- privacy statement.

## Why XGBoost remains server-side

The full XGBoost runtime is unnecessary for the Android baseline. KDR uses the JSON model format for self-hosted experiments and evaluation.

If a learned model materially outperforms `rules-v1`, the preferred Android path is to **distill/export a compact inference representation** after parity tests instead of adding a heavy general ML runtime to an API-23 phone.

Possible future mobile representations include:

- a small linear/logistic model;
- a shallow hand-generated tree ensemble;
- a compact platform-neutral model only if its runtime/dependency cost is justified.

## Model promotion requirements

A trained model should not replace the baseline merely because training accuracy is high. Promotion should require:

1. held-out evaluation;
2. per-class precision/recall/F1;
3. false-positive review, especially for `loan_overdue_collection` and `crb_notice`;
4. class-imbalance analysis;
5. versioned model manifest and rollback;
6. Android/server feature-parity tests;
7. privacy review proving raw communications are absent from the training dataset;
8. review of human-label provenance and duplicate/poisoning risks.

## Legal boundary

A message class is an **evidence-organizing signal**, not a legal finding. For example, `loan_overdue_collection` can direct the Legal Library toward DCP/data-protection questions, but it does not prove harassment, unlawful disclosure, a Data Protection Act breach or a cybercrime.
