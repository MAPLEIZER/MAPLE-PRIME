from __future__ import annotations

import stat
from pathlib import Path
from zipfile import ZipFile

from kdr_installer.macos_package import build_macos_release_zip


def _mode(info) -> int:
    return (info.external_attr >> 16) & 0xFFFF


def test_macos_release_zip_preserves_executable_modes_and_launcher(tmp_path: Path) -> None:
    executable = tmp_path / "kdr-installer"
    executable.write_bytes(b"mock-mach-o")
    executable.chmod(0o755)
    archive = tmp_path / "kdr-installer-macos.zip"

    build_macos_release_zip(executable, archive)

    with ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        assert names == {"kdr-installer", "Run Kenya Data Rights.command", "README.txt"}
        assert bundle.read("kdr-installer") == b"mock-mach-o"
        assert stat.S_IMODE(_mode(bundle.getinfo("kdr-installer"))) == 0o755
        assert stat.S_IMODE(_mode(bundle.getinfo("Run Kenya Data Rights.command"))) == 0o755
        launcher = bundle.read("Run Kenya Data Rights.command").decode("utf-8")
        assert 'exec "$DIR/kdr-installer" "$@"' in launcher
