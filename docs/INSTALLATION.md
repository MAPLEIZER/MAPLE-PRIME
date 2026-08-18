# Installation and self-test

The recommended alpha path is the **KDR Installer** executable. It keeps Docker Compose as the deployment engine but hides routine Compose commands behind a small themed terminal interface.

## Requirements

Only one external dependency is required for the executable path:

- **Docker Desktop** on Windows/macOS, or Docker Engine with **Compose v2** on Linux.

Git, Python and Node.js are **not required** when using a packaged installer executable.

## Installer artifacts

CI builds one-file installers with PyInstaller for:

- Windows: `kdr-installer.exe`
- macOS: `kdr-installer`
- Linux: `kdr-installer`

The same CI run tests the installer package before packaging each executable.

## First run

1. Start Docker Desktop / Docker Engine.
2. Run `kdr-installer`.
3. Choose **Install / first setup**.
4. The installer checks Docker and Compose before changing anything.
5. KDR source is installed into a user-scoped application-data directory.
6. The hardened Docker stack is built and started.
7. The installer immediately runs the full self-test.
8. Choose **Open dashboard** or browse to `http://127.0.0.1:8080`.

Default install locations:

| Platform | Default source location |
|---|---|
| Windows | `%LOCALAPPDATA%\KenyaDataRights` |
| macOS | `~/Library/Application Support/KenyaDataRights` |
| Linux | `${XDG_DATA_HOME:-~/.local/share}/kenya-data-rights` |

Set `KDR_INSTALL_HOME` before launching the installer to override this location.

## TUI menu

The installer exposes these actions:

1. **Install / first setup** — download KDR, build containers and start services.
2. **Start KDR** — start an existing installation.
3. **Run self-test** — validate the complete local user path.
4. **Open dashboard** — open the local dashboard in the default browser.
5. **Show status** — show Compose service status.
6. **Update alpha** — refresh source and rebuild while preserving Docker data.
7. **Repair / rebuild** — rebuild the existing source checkout and containers.
8. **Stop KDR** — stop containers without deleting data.
9. **Uninstall** — remove containers; deleting persistent data is a separate explicit confirmation.
10. **Quit**.

## What self-test verifies

The installer does not treat “containers started” as sufficient. It checks:

- Docker CLI exists;
- Docker daemon is reachable;
- Docker Compose v2 is available;
- FastAPI is reachable directly on loopback;
- the web dashboard is reachable;
- nginx can proxy to the API;
- the API's internal integrity endpoint passes;
- SQLite and snapshot storage are writable.

The API internal self-test checks the database, approved-source manifest and snapshot storage without fetching or modifying regulator data.

## Data safety

A normal **Stop**, **Update**, **Repair** or **Uninstall** does not delete the KDR Docker data volume.

A destructive volume purge requires a separate prompt and a second confirmation. This is the only installer path that intentionally removes the local database and stored regulator snapshots.

## Manual fallback

If the executable cannot be used, the underlying deployment remains normal Docker Compose:

```bash
git clone https://github.com/MAPLEIZER/kenya-data-rights.git
cd kenya-data-rights
git checkout agent/alpha-0-30
docker compose -f deploy/docker-compose/compose.yaml up --build -d
```

Health checks:

```text
http://127.0.0.1:8000/api/v1/health
http://127.0.0.1:8080/
http://127.0.0.1:8080/api/v1/health
http://127.0.0.1:8080/api/v1/system/self-test
```

## Hands-on alpha acceptance test

The final human acceptance pass should be performed on a normal personal machine rather than CI:

1. Run the installer from a clean directory.
2. Confirm the TUI correctly detects Docker.
3. Install and let the automatic self-test finish.
4. Open the dashboard from the installer.
5. Restart the computer or Docker and confirm **Start KDR** restores the same data.
6. Run source sync from the dashboard and inspect any source-specific warnings.
7. Run reconciliation only after both alpha sources are available.
8. Restart KDR and confirm persisted source/review state remains.
9. Run **Repair / rebuild** and verify data remains.
10. Run **Uninstall** without purge and verify reinstall can reuse the preserved Docker volume.

Record any machine/OS-specific issues as GitHub issues before tagging the public alpha.
