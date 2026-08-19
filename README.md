<div align="center">

# Kenya Data Rights

### Local-first privacy, regulatory intelligence and digital-rights tooling for Kenya

[![CI](https://github.com/MAPLEIZER/kenya-data-rights/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/MAPLEIZER/kenya-data-rights/actions/workflows/ci.yml)
[![CodeQL](https://github.com/MAPLEIZER/kenya-data-rights/actions/workflows/codeql.yml/badge.svg?branch=master)](https://github.com/MAPLEIZER/kenya-data-rights/actions/workflows/codeql.yml)
![Android](https://img.shields.io/badge/Android-6.0%2B-3DDC84)
![Python](https://img.shields.io/badge/Python-3.12-3776AB)
![License](https://img.shields.io/badge/license-Apache%202.0-blue)

**CBK + ODPC intelligence · Android DCP identification · legal teaching · civic participation · local-first privacy**

[Download](https://github.com/MAPLEIZER/kenya-data-rights/releases) · [Install](#install-in-minutes) · [Android](#android-companion) · [Legal Library](#legal-library) · [Security](#privacy--security) · [Docs](#documentation)

</div>

---

> [!IMPORTANT]
> **KDR is an alpha research/rights tool, not a blacklist or legal decision engine.** A regulator record not found in a reviewed snapshot does not automatically mean an institution is unregistered, unlicensed, unlawful or non-compliant. A message classification is evidence organization, not a legal finding.

## What is KDR?

Kenya Data Rights (KDR) is an open-source platform for understanding who may hold or use your personal/credit information, mapping digital-credit apps and sender identities to regulated providers, exercising data rights, and learning how Kenyan privacy/cyber/digital-credit law applies.

It is designed to run on **your own machine first**.

```text
CBK licensed/listed institution
        ≠
ODPC controller/processor observation
        ≠
CRB regulatory/subscriber status
        ≠
proof a lender submitted THIS person's information
        ≠
ODPC determination
        ≠
final court outcome
```

KDR preserves those distinctions throughout the data model and UI.

## Alpha at a glance

| Area | Current alpha |
|---|---|
| **Regulatory intelligence** | Controlled CBK/ODPC ingest, immutable snapshots, provenance, conservative reconciliation |
| **Dashboard** | Source status, sync, reports, manual Confirm/Reject review |
| **Legal Library** | Searchable Kenyan privacy, DCP, CRB, cybercrime, access and consumer-law teaching material |
| **Civic Participation** | Official-consultation discovery + user-reviewed memorandum/email drafts with anti-spam boundaries |
| **Android** | Android 6.0+, local loan-message classifier, Share flow, optional foreground SMS/Call Log direct build |
| **Self-hosted learning** | Android → your KDR server derived-feature telemetry; raw SMS excluded from telemetry schema |
| **ML experiments** | Optional labeled-only XGBoost training pipeline; no heavy ML runtime required on phone |
| **Installer** | Themed Windows/Linux one-file executables plus an executable-preserving macOS ZIP, self-test, updates, Android pairing |
| **Security** | Localhost defaults, restricted Tailscale mobile path, bearer auth, Keystore pairing, hardened containers |
| **Engineering** | Test-first RED → GREEN rule, Alembic migrations, CodeQL, dependency locks/audits |

# Install in minutes

## 1. Install Docker

- Windows/macOS: Docker Desktop
- Linux: Docker Engine + Compose v2

Git, Python and Node.js are **not required** for the packaged-installer path.

## 2. Download KDR

Open **[GitHub Releases](https://github.com/MAPLEIZER/kenya-data-rights/releases)** and use the latest tested alpha assets:

```text
Windows   kdr-installer-windows-x86_64.exe
macOS     kdr-installer-macos.zip
Linux     kdr-installer-linux-x86_64
Android   kdr-android-direct-alpha.apk
          kdr-android-play-alpha.apk
```

A successful newest alpha CI build is published as the rolling prerelease **`alpha-latest`**, together with `SHA256SUMS.txt`.

## 3. Run the installer

### Windows

Double-click:

```text
kdr-installer-windows-x86_64.exe
```

### macOS

1. Download and extract `kdr-installer-macos.zip`.
2. Double-click **Run Kenya Data Rights.command** inside the extracted folder.
3. If Gatekeeper warns about an unsigned alpha build, Control-click the launcher, choose **Open**, then confirm **Open**. Do not disable Gatekeeper globally.

The ZIP preserves the Unix executable metadata that is lost when a raw Mach-O binary is downloaded directly from a GitHub Release asset.

### Linux

```bash
chmod +x kdr-installer-linux-x86_64
./kdr-installer-linux-x86_64
```

Then choose **Install / first setup**.

## Installer TUI

```text
╭──────────────────── Kenya Data Rights ────────────────────╮
│ KDR Installer · local-first alpha                         │
│                                                          │
│  1  Install / first setup                                │
│  2  Start KDR                                            │
│  3  Run self-test                                        │
│  4  Open dashboard                                       │
│  5  Show status                                          │
│  6  Check / install update                               │
│  7  Update preferences                                   │
│  8  Pair Android                                         │
│  9  Open GitHub Releases                                 │
│ 10  Repair / rebuild                                     │
│ 11  Stop KDR                                             │
│ 12  Uninstall                                            │
│ 13  Quit                                                 │
╰──────────────────────────────────────────────────────────╯
```

Application updates can be **Prompt**, **Automatic**, or **Manual**. Updates and repairs preserve the persistent KDR data volume.

The installer records the exact CI-tested source commit instead of blindly tracking a moving branch.

See [`docs/INSTALLATION.md`](docs/INSTALLATION.md).

## Local dashboard

After installation:

```text
Dashboard       http://127.0.0.1:8080
API health      http://127.0.0.1:8000/api/v1/health
Internal test   http://127.0.0.1:8080/api/v1/system/self-test
```

## What you can do

<table>
<tr>
<td width="50%" valign="top">

### Regulatory explorer

- sync approved CBK and ODPC sources;
- preserve retrieved source bytes and SHA-256 provenance;
- fail closed on parser/cardinality drift;
- distinguish regulator status from subject-specific evidence.

</td>
<td width="50%" valign="top">

### Reconciliation review

- compare CBK and ODPC observations;
- inspect candidate matches and “not located” findings;
- manually Confirm/Reject links;
- preserve source evidence independently of reviewer decisions.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### Legal Library

- search authoritative Kenyan privacy/cyber/DCP/CRB references;
- learn from readable chapters;
- follow official-source links and version dates;
- use message classifications to find **possible** relevant law without declaring a breach.

</td>
<td width="50%" valign="top">

### Civic Participation

- check allowlisted official government/Parliament/ODPC pages for relevant AI/cyber/privacy consultations;
- review discovery candidates;
- draft one memorandum from your own points;
- open official forms or a prefilled `mailto:` draft;
- never bulk-submit or silently send.

</td>
</tr>
</table>

# Android companion

KDR ships two Android flavors targeting API 36 with **minSdk 23 / Android 6.0+**.

### Direct/private APK

`kdr-android-direct-alpha.apk`

- explicit foreground `READ_SMS` + `READ_CALL_LOG` test flow;
- bounded recent scan;
- no SMS/call receiver or background service;
- activity foreground checks stop scans when you leave the app;
- raw message bodies are not persisted;
- local loan-message classification.

Android may refuse hard-restricted SMS/Call Log grants depending on installer/role/OEM policy. KDR does not bypass that platform control.

### Play-compatible APK

`kdr-android-play-alpha.apk`

- no `READ_SMS` or `READ_CALL_LOG` permission;
- receives one user-selected message through Android Share;
- local classification and optional explicit derived-feature upload.

# Legal Library

The dashboard includes a searchable library grounded in Kenya-specific official sources and source metadata. It is designed for education and evidence organization rather than automated legal conclusions.

# Privacy & Security

KDR defaults to local-only operation. The dashboard/API remain bound to loopback unless the user explicitly enables the limited mobile pairing path. Raw SMS bodies are excluded from mobile telemetry, and public evidence is kept separate from reviewer conclusions.

# Documentation

See the `docs/` directory for installation, Android testing, architecture, pricing methodology, app identity, civic participation and legal-source documentation.
