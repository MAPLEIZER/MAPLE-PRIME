from __future__ import annotations

import hashlib
import json
import platform
import re
import urllib.request
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

from kdr_installer import __version__
from kdr_installer.network import trusted_urlopen

REPOSITORY = "MAPLEIZER/kenya-data-rights"
ALPHA_RELEASE_TAG = "alpha-latest"
_VERSION_RE = re.compile(
    r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:(?:-?alpha\.?|a)(?P<alpha>\d+))?$",
    re.IGNORECASE,
)
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class UpdateMode(str, Enum):
    PROMPT = "prompt"
    AUTO = "auto"
    MANUAL = "manual"


@dataclass(frozen=True)
class InstallerPreferences:
    update_mode: UpdateMode = UpdateMode.PROMPT


@dataclass(frozen=True)
class InstallState:
    source_sha: str | None = None
    release_tag: str | None = None
    installed_version: str | None = None


@dataclass(frozen=True)
class ReleaseInfo:
    tag: str
    source_sha: str
    html_url: str
    published_at: str | None
    assets: dict[str, str]


def parse_version(value: str) -> tuple[int, int, int, int, int]:
    match = _VERSION_RE.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"unsupported version: {value}")
    alpha = match.group("alpha")
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        1 if alpha is None else 0,
        0 if alpha is None else int(alpha),
    )


def is_newer_release(current: str, candidate: str) -> bool:
    return parse_version(candidate) > parse_version(current)


def release_asset_name(system: str | None = None, machine: str | None = None) -> str:
    system = system or platform.system()
    machine = (machine or platform.machine()).lower()
    if system == "Windows":
        return "kdr-installer-windows-x86_64.exe"
    if system == "Linux":
        return "kdr-installer-linux-x86_64"
    if system == "Darwin":
        return "kdr-installer-macos"
    raise ValueError(f"unsupported installer platform: {system}/{machine}")


def parse_checksums(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) != 2 or not _SHA256_RE.fullmatch(parts[0]):
            continue
        name = parts[1].lstrip("*").strip()
        if name and "/" not in name and "\\" not in name:
            result[name] = parts[0].lower()
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _config_dir(root: Path) -> Path:
    return root / ".kdr"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        temporary.chmod(0o600)
    except OSError:
        pass
    temporary.replace(path)


def load_preferences(root: Path) -> InstallerPreferences:
    path = _config_dir(root) / "preferences.json"
    if not path.is_file():
        return InstallerPreferences()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return InstallerPreferences(update_mode=UpdateMode(payload.get("update_mode", "prompt")))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return InstallerPreferences()


def save_preferences(root: Path, preferences: InstallerPreferences) -> None:
    _write_json(_config_dir(root) / "preferences.json", {"update_mode": preferences.update_mode.value})


def load_install_state(root: Path) -> InstallState:
    path = _config_dir(root) / "install-state.json"
    if not path.is_file():
        return InstallState()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return InstallState(
            source_sha=payload.get("source_sha"),
            release_tag=payload.get("release_tag"),
            installed_version=payload.get("installed_version"),
        )
    except (OSError, TypeError, json.JSONDecodeError):
        return InstallState()


def save_install_state(root: Path, state: InstallState) -> None:
    _write_json(_config_dir(root) / "install-state.json", asdict(state))


def fetch_alpha_release(timeout: int = 8) -> ReleaseInfo:
    url = f"https://api.github.com/repos/{REPOSITORY}/releases/tags/{ALPHA_RELEASE_TAG}"
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": f"KDR-Installer/{__version__}"},
    )
    with trusted_urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    assets = {
        item["name"]: item["browser_download_url"]
        for item in payload.get("assets", [])
        if isinstance(item, dict) and item.get("name") and item.get("browser_download_url")
    }
    source_sha = str(payload.get("target_commitish", ""))
    if not re.fullmatch(r"[0-9a-fA-F]{40}", source_sha):
        raise ValueError("alpha release is not pinned to an exact source commit")
    return ReleaseInfo(
        tag=str(payload.get("tag_name", ALPHA_RELEASE_TAG)),
        source_sha=source_sha.lower(),
        html_url=str(payload.get("html_url", f"https://github.com/{REPOSITORY}/releases")),
        published_at=payload.get("published_at"),
        assets=assets,
    )


def update_available(root: Path, release: ReleaseInfo) -> bool:
    state = load_install_state(root)
    return state.source_sha != release.source_sha
