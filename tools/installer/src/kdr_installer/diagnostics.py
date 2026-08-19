from __future__ import annotations

import json
import logging
import os
import platform
import re
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable

from kdr_installer import __version__
from kdr_installer.core import COMPOSE_RELATIVE, RUNTIME_ENV_RELATIVE, run

SELF_TEST_URL = "http://127.0.0.1:8080/api/v1/system/self-test"
MAX_SECTION_CHARS = 500_000
LOGGER_NAME = "kdr_installer"

_SECRET_PATTERNS = [
    re.compile(r"(?i)(KDR_MOBILE_API_TOKEN\s*[:=]\s*['\"]?)([^\s,'\"]+)(['\"]?)"),
    re.compile(r"(?i)(['\"]?mobile_api_token['\"]?\s*[:=]\s*['\"]?)([^\s,'\"]+)(['\"]?)"),
    re.compile(r"(?i)(['\"]?pairing_token['\"]?\s*[:=]\s*['\"]?)([^\s,'\"]+)(['\"]?)"),
    re.compile(r"(?i)(pairing token\s*[:=]\s*)([^\s]+)"),
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)([^\s]+)"),
]


def redact_text(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: f"{match.group(1)}<redacted>{match.group(3) if match.lastindex and match.lastindex >= 3 else ''}", redacted)
    return redacted


class _RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact_text(super().format(record))


def installer_log_path(root: Path) -> Path:
    return root / ".kdr" / "logs" / "installer.log"


def configure_installer_logging(root: Path) -> Path | None:
    path = installer_log_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    target = str(path.resolve())
    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler) and getattr(handler, "baseFilename", None) == target:
            return path

    try:
        handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    except OSError:
        return None
    handler.setFormatter(
        _RedactingFormatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z")
    )
    logger.addHandler(handler)
    logger.info("installer logging started version=%s", __version__)
    return path


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def _bounded(text: str) -> str:
    text = redact_text(text)
    if len(text) <= MAX_SECTION_CHARS:
        return text
    return text[-MAX_SECTION_CHARS:] + "\n[output truncated to the most recent diagnostic data]\n"


def _compose_prefix(root: Path) -> list[str]:
    prefix = ["docker", "compose"]
    runtime_env = root / RUNTIME_ENV_RELATIVE
    if runtime_env.is_file():
        prefix.extend(["--env-file", str(runtime_env)])
    prefix.extend(["-f", str(root / COMPOSE_RELATIVE)])
    return prefix


def _command_text(
    args: list[str],
    *,
    root: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> str:
    try:
        completed = runner(args, cwd=root, check=False)
    except Exception as exc:
        return f"command failed before execution: {type(exc).__name__}\n"
    return _bounded(
        f"$ {' '.join(str(value) for value in args)}\n"
        f"returncode={completed.returncode}\n"
        f"--- stdout ---\n{completed.stdout or ''}\n"
        f"--- stderr ---\n{completed.stderr or ''}\n"
    )


def _load_selftest() -> dict[str, object]:
    request = urllib.request.Request(
        SELF_TEST_URL,
        headers={"User-Agent": f"KDR-Installer/{__version__}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload if isinstance(payload, dict) else {"ok": False, "error_type": "UnexpectedPayload"}
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return {"ok": False, "available": False, "error_type": type(exc).__name__}


def _container_manifest_probe() -> str:
    return (
        "from pathlib import Path; import hashlib,json; "
        "from app.core.config import get_settings; from app.services.sources import load_manifest; "
        "p=Path(get_settings().source_manifest_path); "
        "d={'configured_path':str(p),'exists':p.exists(),'is_file':p.is_file()}; "
        "data=p.read_bytes() if p.is_file() else b''; "
        "d.update({'size_bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}) if data else None; "
        "exec(\"try:\\n m=load_manifest(p); d.update({'parse_ok':True,'source_count':len(m.sources)})\\n"
        "except Exception as e:\\n d.update({'parse_ok':False,'error_type':type(e).__name__})\"); "
        "print(json.dumps(d,sort_keys=True))"
    )


def _default_output_dir() -> Path:
    desktop = Path.home() / "Desktop"
    return desktop if desktop.is_dir() else Path.home()


def export_support_bundle(
    root: Path,
    *,
    output_dir: Path | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = run,
    selftest_loader: Callable[[], dict[str, object]] = _load_selftest,
) -> Path:
    output = output_dir or _default_output_dir()
    output.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%SZ")
    destination = output / f"KDR-support-{timestamp}.zip"

    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "installer_version": __version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "frozen_executable": bool(getattr(sys, "frozen", False)),
        "install_root": str(root),
        "privacy": {
            "runtime_env_contents_included": False,
            "database_contents_included": False,
            "snapshot_contents_included": False,
            "message_or_telemetry_contents_included": False,
            "known_tokens_redacted": True,
        },
    }

    compose = _compose_prefix(root)
    sections: dict[str, str] = {
        "summary.json": json.dumps(summary, indent=2, sort_keys=True) + "\n",
        "self-test.json": json.dumps(selftest_loader(), indent=2, sort_keys=True, default=str) + "\n",
        "docker-version.txt": _command_text(["docker", "version"], root=root, runner=runner),
        "compose-version.txt": _command_text(["docker", "compose", "version"], root=root, runner=runner),
        "compose-ps.txt": _command_text([*compose, "ps", "--all"], root=root, runner=runner),
        "api-logs.txt": _command_text([*compose, "logs", "--no-color", "--tail", "500", "api"], root=root, runner=runner),
        "web-logs.txt": _command_text([*compose, "logs", "--no-color", "--tail", "200", "web"], root=root, runner=runner),
        "api-data-init-logs.txt": _command_text([*compose, "logs", "--no-color", "--tail", "100", "api-data-init"], root=root, runner=runner),
        "container-manifest.txt": _command_text(
            [*compose, "exec", "-T", "api", "python", "-c", _container_manifest_probe()],
            root=root,
            runner=runner,
        ),
    }

    state_path = root / ".kdr" / "install-state.json"
    if state_path.is_file():
        try:
            sections["install-state.json"] = state_path.read_text(encoding="utf-8")
        except OSError:
            sections["install-state.json"] = "unreadable\n"

    log_path = installer_log_path(root)
    if log_path.is_file():
        try:
            sections["installer.log"] = log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            sections["installer.log"] = "unreadable\n"
    else:
        sections["installer.log"] = "installer log not available\n"

    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sections.items():
            archive.writestr(name, _bounded(content))

    try:
        os.chmod(destination, 0o600)
    except OSError:
        pass
    get_logger().info("support bundle exported path=%s", destination)
    return destination
