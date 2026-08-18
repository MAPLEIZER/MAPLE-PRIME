from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, text

from app.services.sources import load_manifest


def _result(ok: bool, detail: str) -> dict[str, object]:
    return {"ok": ok, "detail": detail}


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
        )
    except (OSError, ValueError):
        checks["source_manifest"] = _result(False, "approved source manifest is missing or invalid")

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
