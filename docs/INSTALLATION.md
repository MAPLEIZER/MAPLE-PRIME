# Installation, updates and self-test

The recommended KDR alpha path is the **KDR Installer** executable. It keeps Docker Compose as the deployment engine while hiding routine Docker commands behind a themed terminal interface.

## Fastest path

The primary download surface is the repository **GitHub Releases** page. Successful alpha CI builds are published as a rolling prerelease named `alpha-latest`; milestone tags remain separate immutable releases.

Expected release assets:

```text
kdr-installer-windows-x86_64.exe
kdr-installer-macos
kdr-installer-linux-x86_64
kdr-android-direct-alpha.apk
kdr-android-play-alpha.apk
kdr-android-test-package.zip
SHA256SUMS.txt
```

The installer executable does **not** require Git, Python or Node.js. It does require Docker.

## Windows

1. Install/start Docker Desktop.
2. Open the KDR GitHub Releases page and choose **Kenya Data Rights — latest tested alpha**.
3. Download `kdr-installer-windows-x86_64.exe` and optionally verify it against `SHA256SUMS.txt`.
4. Run the executable.
5. Choose **Install / first setup**.
6. Let the automatic KDR self-test finish.
7. Choose **Open dashboard**.

No command prompt is required for the normal path.

## macOS

1. Install/start Docker Desktop.
2. Download `kdr-installer-macos` from the latest tested alpha release.
3. In Terminal, make the unsigned alpha binary executable:

```bash
chmod +x ~/Downloads/kdr-installer-macos
~/Downloads/kdr-installer-macos
```

For an unsigned development build, macOS may require the normal Finder/System Settings approval flow. Do **not** disable Gatekeeper globally.

4. Choose **Install / first setup**.
5. Let the self-test finish and open the dashboard.

Code-signing/notarization should be added before presenting KDR as a polished public macOS application.

## Linux

Install Docker Engine and Docker Compose v2, then:

```bash
chmod +x kdr-installer-linux-x86_64
./kdr-installer-linux-x86_64
```

Choose **Install / first setup**.

## Installer menu

The current TUI exposes:

1. **Install / first setup** — use the newest tested alpha source and build/start KDR.
2. **Start KDR** — start an existing installation.
3. **Run self-test** — verify Docker, API, dashboard, proxy and persistence.
4. **Open dashboard** — open `http://127.0.0.1:8080`.
5. **Show status** — display Compose service state.
6. **Check / install update** — install the newest tested alpha without deleting data.
7. **Update preferences** — choose Prompt, Automatic or Manual application updates.
8. **Pair Android** — enable privacy-minimized mobile telemetry and create a pairing token.
9. **Open GitHub Releases** — find installers, APKs, checksums and notes.
10. **Repair / rebuild** — rebuild the local stack while preserving data.
11. **Stop KDR** — stop services while preserving data.
12. **Uninstall** — remove application containers/files; data deletion is separately confirmed.
13. **Quit**.

## Update behavior

KDR stores update preferences under the user-scoped installation directory in `.kdr/preferences.json`.

Three application update modes are supported:

- **Prompt** — when the installer starts, offer the newest CI-tested alpha if the installed source SHA differs.
- **Automatic** — when the installer starts, update the KDR application source/containers to the newest tested alpha automatically.
- **Manual** — check only when **Check / install update** is selected.

The rolling release points to an exact Git commit. The installer records that exact source SHA in `.kdr/install-state.json`, so updates are not based on an ambiguous moving branch checkout.

Application updates preserve `.kdr` installer configuration and the persistent Docker data volume.

### Updating the installer executable itself

The installer deliberately does not overwrite its currently running executable. Cross-platform self-replacement is fragile, and Windows normally locks a running executable. New installer binaries are published on GitHub Releases with `SHA256SUMS.txt`; use **Open GitHub Releases** to replace the executable when desired.

This separation means KDR can safely update the installed application stack without relying on self-modifying executable behavior.

## Android pairing with a Mac/self-hosted machine

Choose **Pair Android** in the desktop installer.

The installer:

1. generates a high-entropy mobile bearer token;
2. stores it in `.kdr/runtime.env` with restrictive file permissions where supported;
3. enables the derived-feature telemetry API;
4. rebuilds/restarts the local API with the new configuration;
5. if Tailscale is installed and you approve it, configures Tailscale Serve for **only** `/api/v1/mobile/` → `127.0.0.1:8000`;
6. displays the HTTPS server URL and pairing token for entry in the Android app.

The dashboard is **not** exposed by the pairing flow. Regulatory sync/reconciliation, Legal Library and Civic Participation remain loopback-only. The remote mobile path still requires the bearer token and remains subject to Tailscale access controls.

Running **Pair Android** again rotates the token.

## What mobile telemetry contains

Mobile telemetry is disabled until you pair it. Android upload is then still manual.

The server accepts a fixed `kdr-msg-v1` feature schema containing bounded numeric/boolean features and 64 hashed token buckets. It does **not** accept arbitrary raw-message fields. The server hashes the app client ID before persistence.

A bulk SMS scan can send unlabeled derived observations. A human training label is accepted by the Android UI only for **one message explicitly shared into KDR**, preventing one click from labeling an entire inbox scan.

## Self-test

The installer checks:

- Docker CLI;
- Docker daemon;
- Docker Compose v2;
- direct FastAPI health;
- dashboard health;
- nginx → API proxying;
- API internal integrity checks;
- SQLite writability;
- snapshot-storage writability;
- approved source-manifest availability.

A successful self-test means the local application path is ready for hands-on use; it does not claim that live regulator websites or Android OEM permission behavior have been validated on your hardware.

## Data safety

Normal **Stop**, **Update**, **Repair** and ordinary **Uninstall** operations preserve the KDR Docker data volume.

Deleting the database/snapshots is a separate destructive choice and requires a second explicit confirmation.

Default source/config locations:

| Platform | Installation directory |
|---|---|
| Windows | `%LOCALAPPDATA%\KenyaDataRights` |
| macOS | `~/Library/Application Support/KenyaDataRights` |
| Linux | `${XDG_DATA_HOME:-~/.local/share}/kenya-data-rights` |

Set `KDR_INSTALL_HOME` before launching the installer to override the location.

## Manual Docker fallback

```bash
git clone https://github.com/MAPLEIZER/kenya-data-rights.git
cd kenya-data-rights
git checkout agent/alpha-0-30
docker compose -f deploy/docker-compose/compose.yaml up --build -d
```

Health endpoints:

```text
http://127.0.0.1:8000/api/v1/health
http://127.0.0.1:8080/
http://127.0.0.1:8080/api/v1/health
http://127.0.0.1:8080/api/v1/system/self-test
```

## Final hands-on alpha acceptance pass

The remaining human test should cover what hosted CI cannot truthfully prove:

1. run the packaged installer on the target personal machine;
2. verify Install, Start, Stop, Update, Repair and non-destructive Uninstall;
3. verify automatic/prompt/manual application update behavior;
4. confirm persistent data survives restart/rebuild;
5. run the live CBK sync and validate the current parser/cardinality invariant;
6. run the live ODPC sync and record any public-site challenge behavior without bypassing controls;
7. review representative reconciliation findings;
8. pair the Android direct APK with the Mac/self-hosted server over approved HTTPS/Tailscale;
9. verify only the mobile API is remotely exposed;
10. test foreground SMS/Call Log behavior on the real Android device;
11. verify derived telemetry reaches the server but raw SMS bodies do not;
12. Share one message into KDR, correct/confirm its class, send it, and verify only that one sample receives a human label;
13. independently test the permission-free Play/Share APK.

Record machine/OEM-specific issues before merging PR #1 or tagging the first milestone alpha.
