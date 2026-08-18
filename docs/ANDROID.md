# Android alpha

KDR now has a native Android shell under `apps/android` using Kotlin + Jetpack Compose.

## Compatibility

- `minSdk = 23` — Android 6.0+
- `targetSdk = 36`
- `compileSdk = 36`
- JDK 17
- Android Gradle Plugin 9.4
- Gradle 9.6
- Stable Compose BOM

API 23 is the project compatibility floor because current AndroidX moved its default minimum to API 23. Lowering below 23 would require intentionally pinning older framework dependencies and would reduce maintenance/security headroom.

## Two distribution flavors

### `direct`

The direct/sideload flavor declares:

- `android.permission.READ_SMS`
- `android.permission.READ_CALL_LOG`

It is intended for private/self-hosted testing and other distribution paths where the user knowingly installs the APK outside Google Play.

The permissions are runtime-requested only when the user presses **Scan recent SMS & calls**.

### `play`

The Play-compatible flavor declares neither restricted permission. It uses Android's explicit Share flow instead.

This split prevents a future Play build from silently inheriting restricted permissions merely because the direct APK needs them.

## Foreground-only communication access

Android does not provide a special “while using the app” grant mode for `READ_SMS` or `READ_CALL_LOG`. KDR therefore enforces this at the application layer:

- no SMS receiver;
- no call-log receiver;
- no foreground/background service for communications;
- no WorkManager/scheduled communication scan;
- access starts only after an explicit visible button press;
- scanning is permitted only while the activity is `RESUMED`;
- an in-memory foreground flag is checked throughout the content-provider loops;
- `onPause()` immediately disables further reads;
- ephemeral scan results are cleared when the app loses the foreground.

## Data minimization

The direct alpha currently scans at most:

- 250 SMS inbox rows;
- 250 call-log rows;
- from the last 90 days.

For each SMS row, the body is read into a loop-local string, immediately passed through the minimizer and then allowed to fall out of scope. Raw message bodies are not written to KDR files, preferences, SQLite, logs or the server API.

For call logs, only number, cached display name and date are requested. Call duration is not queried.

The in-memory result contains only candidate phone identifiers and candidate labels. Results are cleared on foreground loss.

## Server boundary

The existing KDR server contribution contract still does **not** accept unrestricted raw SMS or call-log data. The Android shell does not upload its scan results yet. The **Review mapping before sharing** control is intentionally non-networked until the consent/review and local-DCP matching flow is complete.

This means the sensitive scanning feature can be exercised locally before any crowdsourced enrichment path exists.

## Google Play policy boundary

Google Play treats SMS and Call Log permissions as highly restricted. The current KDR mapping/research purpose does not fit the ordinary default-SMS/default-Phone/default-Assistant handler requirement and should not be represented as eligible for Play distribution without an approved policy basis.

For that reason:

- `direct` is the restricted-permission sideload build;
- `play` remains permission-free;
- CI fails if the base/Play manifest gains restricted SMS/Call Log permissions;
- CI also fails if a background service or receiver is added to the direct communication flavor.

## Build locally

From `apps/android` with JDK 17 and Android SDK 36 installed:

```bash
gradle testDirectDebugUnitTest testPlayDebugUnitTest

gradle assembleDirectDebug assemblePlayDebug
```

Outputs:

```text
app/build/outputs/apk/direct/debug/app-direct-debug.apk
app/build/outputs/apk/play/debug/app-play-debug.apk
```

CI uploads both APKs as workflow artifacts.

## Direct APK hands-on test

1. Install `app-direct-debug.apk` on an Android 6.0+ test/personal phone.
2. Open KDR and verify no scan starts automatically.
3. Press **Scan recent SMS & calls**.
4. Review the Android permission prompts and grant only if comfortable.
5. Confirm candidate identifiers appear without raw message text.
6. Switch to another app while scanning and confirm KDR stops/clears the ephemeral result.
7. Re-open KDR; confirm the previous scan is not restored.
8. Deny one/both permissions and verify KDR reports that nothing was read.
9. Test Android Share → KDR with a single text message.
10. Verify no KDR Android app data contains copied SMS bodies or call history before enabling any future contribution feature.
