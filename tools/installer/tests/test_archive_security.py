from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZipInfo

import pytest

import kdr_installer.core as core
from kdr_installer.core import _copy_bounded, _safe_extract


def _archive(entries: list[tuple[ZipInfo | str, bytes]]) -> ZipFile:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, payload in entries:
            archive.writestr(name, payload)
    buffer.seek(0)
    return ZipFile(buffer)


def test_safe_extract_rejects_parent_path_traversal(tmp_path: Path):
    archive = _archive([("repo/../../escape.txt", b"nope")])
    with archive, pytest.raises(ValueError, match="unsafe path"):
        _safe_extract(archive, tmp_path / "extract")


def test_safe_extract_rejects_zip_symlink(tmp_path: Path):
    link = ZipInfo("repo/link")
    link.create_system = 3
    link.external_attr = (0o120777 << 16)
    archive = _archive([(link, b"../../outside")])
    with archive, pytest.raises(ValueError, match="symlink"):
        _safe_extract(archive, tmp_path / "extract")


def test_safe_extract_rejects_excessive_uncompressed_size(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(core, "MAX_EXTRACTED_BYTES", 5)
    archive = _archive([("repo/large.txt", b"123456")])
    with archive, pytest.raises(ValueError, match="expanded archive exceeds"):
        _safe_extract(archive, tmp_path / "extract")


def test_safe_extract_accepts_single_repository_root(tmp_path: Path):
    archive = _archive([("repo/README.md", b"ok"), ("repo/apps/file.txt", b"ok")])
    with archive:
        root = _safe_extract(archive, tmp_path / "extract")
    assert root.name == "repo"
    assert (root / "README.md").read_bytes() == b"ok"


def test_copy_bounded_fails_closed_when_download_exceeds_limit():
    source = BytesIO(b"a" * 11)
    target = BytesIO()
    with pytest.raises(ValueError, match="download exceeds"):
        _copy_bounded(source, target, max_bytes=10)


def test_copy_bounded_copies_content_within_limit():
    source = BytesIO(b"kdr")
    target = BytesIO()
    assert _copy_bounded(source, target, max_bytes=10) == 3
    assert target.getvalue() == b"kdr"
