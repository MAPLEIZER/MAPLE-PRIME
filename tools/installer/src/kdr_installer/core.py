from __future__ import annotations

import os
import platform
import shutil
import subprocess
import urllib.request
import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory

REPOSITORY = "MAPLEIZER/kenya-data-rights"
SOURCE_REF = os.getenv("KDR_SOURCE_REF", "agent/alpha-0-30")
ARCHIVE_URL = f"https://github.com/{REPOSITORY}/archive/{SOURCE_REF}.zip"
COMPOSE_RELATIVE = Path("deploy/docker-compose/compose.yaml")


class InstallAction(str, Enum):
    INSTALL = "install"
    START = "start"
    SELF_TEST = "self_test"
    OPEN = "open"
    STATUS = "status"
    STOP = "stop"
    UPDATE = "update"
    REPAIR = "repair"
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
        MenuItem(InstallAction.INSTALL, "Install / first setup", "Download KDR and build the local stack"),
        MenuItem(InstallAction.START, "Start KDR", "Start the existing local installation"),
        MenuItem(InstallAction.SELF_TEST, "Run self-test", "Check Docker, API, web, proxy and persistence"),
        MenuItem(InstallAction.OPEN, "Open dashboard", "Open http://127.0.0.1:8080"),
        MenuItem(InstallAction.STATUS, "Show status", "Show Docker Compose service state"),
        MenuItem(InstallAction.UPDATE, "Update alpha", "Refresh source and rebuild without deleting data"),
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
        return [*base, "up", "--build", "-d", "--remove-orphans"]
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
    return [*args[:2], "-f", str(compose_file), *args[2:]]


def _safe_extract(archive: zipfile.ZipFile, destination: Path) -> Path:
    destination = destination.resolve()
    members = archive.infolist()
    for member in members:
        candidate = (destination / member.filename).resolve()
        if destination not in candidate.parents and candidate != destination:
            raise ValueError("archive contains an unsafe path")
    archive.extractall(destination)
    roots = {Path(m.filename).parts[0] for m in members if Path(m.filename).parts}
    if len(roots) != 1:
        raise ValueError("unexpected repository archive layout")
    return destination / next(iter(roots))


def install_source(install_root: Path, *, ref: str = SOURCE_REF) -> None:
    install_root = install_root.expanduser().resolve()
    install_root.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://github.com/{REPOSITORY}/archive/{ref}.zip"
    with TemporaryDirectory(prefix="kdr-install-") as temp_dir:
        temp = Path(temp_dir)
        archive_path = temp / "source.zip"
        request = urllib.request.Request(url, headers={"User-Agent": "KDR-Installer/0.1"})
        with urllib.request.urlopen(request, timeout=60) as response, archive_path.open("wb") as target:
            shutil.copyfileobj(response, target, length=1024 * 1024)
        with zipfile.ZipFile(archive_path) as archive:
            extracted = _safe_extract(archive, temp / "extract")
        staged = temp / "staged"
        shutil.copytree(extracted, staged)
        if install_root.exists():
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
