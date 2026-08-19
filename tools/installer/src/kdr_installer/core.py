from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import urllib.request
import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import BinaryIO

from kdr_installer.network import trusted_urlopen

REPOSITORY = "MAPLEIZER/kenya-data-rights"
SOURCE_REF = os.getenv("KDR_SOURCE_REF", "master")
COMPOSE_RELATIVE = Path("deploy/docker-compose/compose.yaml")
RUNTIME_ENV_RELATIVE = Path(".kdr/runtime.env")
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_EXTRACTED_BYTES = 350 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 20_000
_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


class InstallAction(str, Enum):
    INSTALL = "install"
    START = "start"
    SELF_TEST = "self_test"
    SUPPORT_BUNDLE = "support_bundle"
    SYNC_SOURCES = "sync_sources"
    OPEN = "open"
    STATUS = "status"
    UPDATE = "update"
    UPDATE_SETTINGS = "update_settings"
    CONFIGURE_PROVIDERS = "configure_providers"
    PAIR_ANDROID = "pair_android"
    RELEASES = "releases"
    REPAIR = "repair"
    STOP = "stop"
    UNINSTALL = "uninstall"
    QUIT = "quit"


class SelfTestCheck(str, Enum):
    DOCKER_CLI = "docker_cli"
    DOCKER_DAEMON = "docker_daemon"
    COMPOSE = "compose"
    API_DIRECT = "api_direct"
    WEB = "web"
    API_PROXY = "api_proxy"
    API_INTERNAL = "api_internal"
    PERSISTENCE = "persistence"


@dataclass(frozen=True)
class MenuItem:
    action: InstallAction
    label: str
    description: str


def installer_menu() -> list[MenuItem]:
    return [
        MenuItem(InstallAction.INSTALL, "Install / first setup", "Download the newest tested alpha and build the local stack"),
        MenuItem(InstallAction.START, "Start KDR", "Start the existing local installation"),
        MenuItem(InstallAction.SELF_TEST, "Run self-test", "Check Docker, API, web, proxy and persistence"),
        MenuItem(InstallAction.SUPPORT_BUNDLE, "Export support bundle", "Create a sanitized diagnostic ZIP to share for troubleshooting"),
        MenuItem(InstallAction.SYNC_SOURCES, "Sync regulator sources", "Sync CBK then ODPC with visible stage-by-stage diagnostics"),
        MenuItem(InstallAction.OPEN, "Open dashboard", "Open http://127.0.0.1:8080"),
        MenuItem(InstallAction.STATUS, "Show status", "Show Docker Compose service state"),
        MenuItem(InstallAction.UPDATE, "Check / install update", "Install the newest tested alpha without deleting data"),
        MenuItem(InstallAction.UPDATE_SETTINGS, "Update preferences", "Choose prompt, automatic, or manual application updates"),
        MenuItem(InstallAction.CONFIGURE_PROVIDERS, "Configure data providers", "Use SerpApi for indexed Google Play discovery or the public fallback"),
        MenuItem(InstallAction.PAIR_ANDROID, "Pair Android", "Enable derived-feature telemetry and optionally publish over Tailscale HTTPS"),
        MenuItem(InstallAction.RELEASES, "Open GitHub Releases", "Find installers, APKs, checksums and release notes"),
        MenuItem(InstallAction.REPAIR, "Repair / rebuild", "Rebuild containers while preserving data"),
        MenuItem(InstallAction.STOP, "Stop KDR", "Stop services while preserving data"),
        MenuItem(InstallAction.UNINSTALL, "Uninstall", "Remove containers; data is preserved unless explicitly purged"),
        MenuItem(InstallAction.QUIT, "Quit", "Exit installer"),
    ]


def default_install_root() -> Path:
    override = os.getenv("KDR_INSTALL_HOME")
    if override:
        return Path(override).expanduser()
    system = platform.system()
    if system == "Windows":
        base = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "KenyaDataRights"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "KenyaDataRights"
    base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "kenya-data-rights"


def self_test_plan() -> list[SelfTestCheck]:
    return list(SelfTestCheck)


def compose_args(action: InstallAction, *, purge_data: bool = False) -> list[str]:
    base = ["docker", "compose"]
    if action is InstallAction.INSTALL:
        return [*base, "up", "--build", "-d"]
    if action is InstallAction.START:
        return [*base, "up", "-d"]
    if action in {InstallAction.UPDATE, InstallAction.REPAIR}:
        return [*base, "up", "--build", "-d", "--remove-orphans", "--force-recreate"]
    if action is InstallAction.STATUS:
        return [*base, "ps"]
    if action is InstallAction.STOP:
        return [*base, "stop"]
    if action is InstallAction.UNINSTALL:
        return [*base, "down", "-v"] if purge_data else [*base, "down"]
    raise ValueError(f"{action.value} is not a compose action")


def command_available(name: str) -> bool:
    return shutil.which(name) is not None


def run(args: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=check)


def compose_command(action: InstallAction, install_root: Path, *, purge_data: bool = False) -> list[str]:
    compose_file = install_root / COMPOSE_RELATIVE
    args = compose_args(action, purge_data=purge_data)
    prefix = [*args[:2]]
    runtime_env = install_root / RUNTIME_ENV_RELATIVE
    if runtime_env.is_file():
        prefix.extend(["--env-file", str(runtime_env)])
    return [*prefix, "-f", str(compose_file), *args[2:]]


def _copy_bounded(source: BinaryIO, target: BinaryIO, *, max_bytes: int) -> int:
    copied = 0
    while True:
        chunk = source.read(1024 * 1024)
        if not chunk:
            return copied
        copied += len(chunk)
        if copied > max_bytes:
            raise ValueError("download exceeds installer safety limit")
        target.write(chunk)


def _is_zip_symlink(member: zipfile.ZipInfo) -> bool:
    mode = member.external_attr >> 16
    return (mode & 0o170000) == 0o120000


def _safe_extract(archive: zipfile.ZipFile, destination: Path) -> Path:
    destination = destination.resolve()
    members = archive.infolist()
    if len(members) > MAX_ARCHIVE_MEMBERS:
        raise ValueError("archive contains too many files")
    if sum(member.file_size for member in members) > MAX_EXTRACTED_BYTES:
        raise ValueError("expanded archive exceeds installer safety limit")

    for member in members:
        if _is_zip_symlink(member):
            raise ValueError("archive contains a symlink")
        candidate = (destination / member.filename).resolve()
        if destination not in candidate.parents and candidate != destination:
            raise ValueError("archive contains an unsafe path")

    roots = {Path(m.filename).parts[0] for m in members if Path(m.filename).parts}
    if len(roots) != 1:
        raise ValueError("unexpected repository archive layout")

    archive.extractall(destination)
    return destination / next(iter(roots))


def _archive_url(ref: str) -> str:
    if not ref or ".." in ref or ref.startswith("/"):
        raise ValueError("invalid source ref")
    if _SHA_RE.fullmatch(ref):
        return f"https://github.com/{REPOSITORY}/archive/{ref}.zip"
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", ref):
        raise ValueError("invalid source ref")
    return f"https://github.com/{REPOSITORY}/archive/refs/heads/{ref}.zip"


def install_source(install_root: Path, *, ref: str = SOURCE_REF) -> None:
    install_root = install_root.expanduser().resolve()
    install_root.parent.mkdir(parents=True, exist_ok=True)
    url = _archive_url(ref)

    with TemporaryDirectory(prefix="kdr-install-") as temp_dir:
        temp = Path(temp_dir)
        archive_path = temp / "source.zip"
        request = urllib.request.Request(url, headers={"User-Agent": "KDR-Installer/0.2"})
        with trusted_urlopen(request, timeout=60) as response, archive_path.open("wb") as target:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_ARCHIVE_BYTES:
                raise ValueError("download exceeds installer safety limit")
            _copy_bounded(response, target, max_bytes=MAX_ARCHIVE_BYTES)

        with zipfile.ZipFile(archive_path) as archive:
            extracted = _safe_extract(archive, temp / "extract")

        staged = temp / "staged"
        shutil.copytree(extracted, staged)
        if install_root.exists():
            user_config = install_root / ".kdr"
            if user_config.is_dir():
                shutil.copytree(user_config, staged / ".kdr", dirs_exist_ok=True)
            backup = install_root.with_name(f"{install_root.name}.previous")
            if backup.exists():
                shutil.rmtree(backup)
            install_root.rename(backup)
            try:
                staged.rename(install_root)
            except Exception:
                backup.rename(install_root)
                raise
            shutil.rmtree(backup)
        else:
            staged.rename(install_root)


def has_installation(install_root: Path) -> bool:
    return (install_root / COMPOSE_RELATIVE).is_file()
