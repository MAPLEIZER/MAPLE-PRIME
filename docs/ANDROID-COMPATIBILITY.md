# Android compatibility strategy

KDR keeps `minSdk 23` (Android 6.0) while targeting API 36. Newer Android capabilities are progressively enabled rather than raising the minimum API.

| Capability | API / approach | KDR direction |
|---|---:|---|
| Runtime dangerous permissions | API 23 | Core direct-flavor permission flow |
| Android Keystore AES/GCM pairing secret | API 23 | Used for self-hosted server token |
| Local message classification | API 23 | Core feature |
| HTTPS telemetry | API 23 | Core, explicit upload only |
| Notification channels | API 26 | Add optional consultation/update alert channels |
| Adaptive launcher icons | API 26 | Add resource variants without changing minSdk |
| Platform BiometricPrompt | API 28 | Optional protection for opening sensitive local evidence; AndroidX can bridge older fingerprint devices if adopted |
| Runtime notification permission | API 33 | Request only if/when alerts are enabled |
| System photo picker | API 33 + supported backport paths | Prefer for user-selected evidence rather than broad storage permissions |
| Credential Manager / passkeys | Modern Android/Jetpack | Future hosted-account feature; capability-gated and not required for local mode |

## What API 23 costs

The baseline requires more compatibility branches and prevents assuming modern platform UI/security APIs are always present. It does **not** require weakening HTTPS, Keystore storage, foreground-only scanning, or the privacy-minimized classifier.

KDR should avoid using the low minimum SDK as justification for legacy broad-storage permissions, background communication harvesting or obsolete cryptography.
