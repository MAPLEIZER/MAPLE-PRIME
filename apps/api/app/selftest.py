from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import Engine, text

from app.services.sources import load_manifest


def _result(ok: bool, detail: str, **metadata: object) -> dict[str, object]:
    return {"ok": ok, "detail": detail, **metadata}


def _manifest_metadata(path: Path) -> dict[str, object]:
    metadata: dict[str, object] = {
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
    }
    if not path.is_file():
        return metadata
    try:
        data = path.read_bytes()
    except OSError as exc:
        metadata["readable"] = False
        metadata["read_error_type"] = type(exc).__name__
        return metadata
    metadata.update(
        {
            "readable": True,
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    )
    return metadata


def run_internal_checks(
    *,
    engine: Engine,
    manifest_path: Path,
    snapshot_dir: Path,
) -> dict[str, object]:
    checks: dict[str, dict[str, object]] = {}

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = _result(True, "database connection is writable/available")
    except Exception:
        checks["database"] = _result(False, "database connectivity check failed")

    manifest_meta = _manifest_metadata(manifest_path)
    try:
        manifest = load_manifest(manifest_path)
        count = len(manifest.sources)
        valid = count > 0
        suffix = "source" if count == 1 else "sources"
        checks["source_manifest"] = _result(
            valid,
            f"approved source manifest parsed ({count} {suffix})"
            if valid
            else "approved source manifest contains no sources",
            source_count=count,
            **manifest_meta,
        )
    except Exception as exc:
        checks["source_manifest"] = _result(
            False,
            "approved source manifest file is missing"
            if not manifest_path.is_file()
            else f"approved source manifest parse failed ({type(exc).__name__})",
            error_type=type(exc).__name__,
            **manifest_meta,
        )

    probe = snapshot_dir / ".kdr-selftest"
    try:
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        probe.write_bytes(b"kdr-selftest")
        if probe.read_bytes() != b"kdr-selftest":
            raise OSError("snapshot probe mismatch")
        checks["snapshot_storage"] = _result(True, "snapshot storage is writable")
    except OSError:
        checks["snapshot_storage"] = _result(False, "snapshot storage write/read check failed")
    finally:
        try:
            probe.unlink(missing_ok=True)
        except OSError:
            pass

    return {"ok": all(bool(item["ok"]) for item in checks.values()), "checks": checks}
