# identity_vault

Encrypted identity and high-risk evidence storage.

Local-first target design:

- one encrypted identity payload rather than duplicated plaintext fields;
- Argon2id-derived key when OS keyring is unavailable;
- authenticated encryption (AES-GCM or XChaCha20-Poly1305);
- key stored separately from the application database;
- identity documents ephemeral by default;
- no secrets or PII in logs.
