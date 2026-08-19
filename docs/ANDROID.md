# Android alpha

KDR has a native Kotlin + Jetpack Compose Android client under `apps/android`.

## Compatibility

- `minSdk = 23` — Android 6.0+
- `targetSdk = 36`
- `compileSdk = 36`
- JDK 17
- Android Gradle Plugin 9.3.0
- Gradle 9.5.0
- Kotlin / Compose compiler plugin 2.3.21
- Compose BOM `2026.06.00`

KDR deliberately keeps API 23 as the compatibility floor while capability-gating newer platform features. See [`ANDROID-COMPATIBILITY.md`](ANDROID-COMPATIBILITY.md).

## Distribution flavors

### `direct`

Private/sideload testing build. It declares:

- `android.permission.READ_SMS`
- `android.permission.READ_CALL_LOG`

The permissions are requested only after the user presses **Scan recent SMS & calls**. There is no SMS receiver, call-log receiver, communication service or scheduled scan.

### `play`

The Play-compatible flavor declares neither restricted communication permission. It uses explicit Android **Share → Kenya Data Rights** intake instead.

Both flavors declare normal Internet/network-state capability and keep `android:usesCleartextTraffic="false"`.

## Restricted-permission reality

`READ_SMS` and `READ_CALL_LOG` are hard-restricted on modern Android. A runtime prompt alone may not be sufficient; the installer-of-record/system role/policy can prevent the permission from being granted.

KDR does not bypass this restriction, impersonate a default SMS/Phone handler, use root or make ADB workarounds part of the application.

If the device refuses a grant, KDR reads nothing and the Share workflow remains available.

## Foreground-only communication scan

Android does not offer the same OS-level “while using the app” mode for SMS/Call Log that exists for some other permissions, so KDR enforces the boundary itself:

- scan begins only after a visible foreground button press;
- activity must be `RESUMED`;
- provider loops repeatedly check the foreground flag;
- `onPause()` stops further reads;
- ephemeral results are cleared on foreground loss;
- no background receiver/service/WorkManager scan exists.

Current bounds:

- up to 250 SMS inbox rows;
- up to 250 call-log rows;
- last 90 days;
- call duration is not queried.

## Local classification

SMS bodies exist only as loop-local strings while features are extracted. The app creates the fixed `kdr-msg-v1` derived feature vector and `rules-v1` classification in memory.

Raw SMS text is not stored in app preferences/files/database and is not included in the telemetry schema.

For call logs KDR requests number, cached display name and date only.

## Self-hosted server pairing

The desktop installer has a **Pair Android** action.

It generates:

- an HTTPS server URL, optionally through Tailscale Serve;
- a high-entropy bearer token;
- a server configuration that enables only the mobile telemetry API.

The Android app stores the pairing URL/token encrypted with Android Keystore AES/GCM.

When Tailscale is used, the installer exposes only:

```text
/api/v1/mobile/
```

to the loopback FastAPI service. It does not publish the dashboard/regulator/admin surface through the pairing workflow.

## Telemetry behavior

Telemetry remains opt-in even after pairing.

1. Scan/share and classify locally.
2. Review the classification.
3. Press **Send derived telemetry**.
4. Android sends only the fixed feature vector, prediction metadata and—when allowed—an explicit human label.

The API rejects arbitrary extra fields. The server hashes the Android client ID before persistence.

Leaving the activity foreground stops scan/upload loops and clears ephemeral analysis state.

## Classifier feedback

KDR intentionally prevents bulk labeling:

- a bulk SMS scan cannot receive one blanket human label;
- a user label is available only when exactly **one message was explicitly shared into KDR**;
- the user can confirm/correct its class in the UI;
- the label is transmitted only if **Send derived telemetry** is pressed;
- pending feedback is cleared when the app backgrounds or a new observation replaces it.

Only these explicitly human-labeled rows are eligible for optional model training.

See [`MESSAGE-CLASSIFIER.md`](MESSAGE-CLASSIFIER.md).

## Google Play boundary

Google Play heavily restricts SMS/Call Log permissions. KDR therefore keeps the two-flavor split:

- `direct` — private/sideload restricted-permission testing;
- `play` — permission-free explicit Share intake.

Do not represent the direct mapping/research use case as Play-policy eligible unless KDR later qualifies under an applicable approved policy basis.

## Builds

From `apps/android` with JDK 17 and Android SDK 36:

```bash
gradle testDirectDebugUnitTest testPlayDebugUnitTest
gradle assembleDirectDebug assemblePlayDebug
```

Outputs:

```text
app/build/outputs/apk/direct/debug/app-direct-debug.apk
app/build/outputs/apk/play/debug/app-play-debug.apk
```

## GitHub Releases

Successful newest alpha CI builds are intended to appear directly on the repo Releases page as the rolling `alpha-latest` prerelease.

Assets:

```text
kdr-android-direct-alpha.apk
kdr-android-play-alpha.apk
kdr-android-test-package.zip
SHA256SUMS.txt
```

The combined test ZIP includes both APKs, testing documentation and APK checksums.

## Direct APK hands-on test

1. Install `kdr-android-direct-alpha.apk` on an Android 6.0+ personal/test device.
2. Verify no SMS/call scan begins at startup.
3. Press **Scan recent SMS & calls**.
4. Test grant and denial behavior for SMS/Call Log.
5. If granted, confirm classifications/identifiers appear without raw bodies.
6. Background the app during/after scanning and verify analysis clears.
7. Re-open KDR and verify the previous scan is not restored.
8. Pair it using the URL/token shown by the desktop installer.
9. Verify the HTTPS mobile status/telemetry path works.
10. Send a bulk scan and verify it contains no human labels unless labels were separately created through the single-share path.
11. Share one SMS explicitly into KDR, review/correct the predicted category and send derived telemetry.
12. Verify the server receives derived features + that one label, but not the raw message body.
13. Test the Play APK independently using Share intake without SMS/Call Log permissions.
