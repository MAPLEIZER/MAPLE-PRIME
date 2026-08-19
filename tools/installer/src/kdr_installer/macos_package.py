from __future__ import annotations

import argparse
import stat
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

_LAUNCHER = """#!/bin/zsh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
chmod +x "$DIR/kdr-installer" 2>/dev/null || true
exec "$DIR/kdr-installer" "$@"
"""

_README = """Kenya Data Rights — macOS alpha installer

1. Extract this ZIP using Finder / Archive Utility.
2. Double-click “Run Kenya Data Rights.command”.
3. If macOS warns that the app came from the Internet, Control-click the launcher,
   choose Open, then confirm Open. KDR is currently an unsigned/notarized alpha build.

The archive intentionally preserves Unix executable permissions for both the launcher
and the bundled PyInstaller executable. The launcher only starts kdr-installer from
this extracted folder; it does not bypass Gatekeeper or alter macOS security policy.
"""


def _write_member(bundle: ZipFile, name: str, payload: bytes, mode: int) -> None:
    info = ZipInfo(name)
    info.create_system = 3
    info.compress_type = ZIP_DEFLATED
    info.external_attr = (stat.S_IFREG | mode) << 16
    bundle.writestr(info, payload)


def build_macos_release_zip(executable: Path, output: Path) -> Path:
    if not executable.is_file():
        raise FileNotFoundError(executable)
    payload = executable.read_bytes()
    if not payload:
        raise ValueError("macOS installer executable is empty")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    try:
        with ZipFile(temporary, "w") as bundle:
            _write_member(bundle, "kdr-installer", payload, 0o755)
            _write_member(bundle, "Run Kenya Data Rights.command", _LAUNCHER.encode("utf-8"), 0o755)
            _write_member(bundle, "README.txt", _README.encode("utf-8"), 0o644)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Package the KDR macOS installer for GitHub Releases")
    parser.add_argument("executable", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build_macos_release_zip(args.executable, args.output)


if __name__ == "__main__":
    main()
