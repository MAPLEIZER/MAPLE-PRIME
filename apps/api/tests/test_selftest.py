from pathlib import Path

from sqlalchemy import create_engine

from app.selftest import run_internal_checks


def test_internal_selftest_checks_database_manifest_and_snapshot_storage(tmp_path: Path):
    manifest = tmp_path / "source-manifest.yaml"
    manifest.write_text("sources: []\n", encoding="utf-8")
    snapshot_dir = tmp_path / "snapshots"
    engine = create_engine("sqlite:///:memory:")

    report = run_internal_checks(
        engine=engine,
        manifest_path=manifest,
        snapshot_dir=snapshot_dir,
    )

    assert report["ok"] is True
    assert report["checks"]["database"]["ok"] is True
    assert report["checks"]["source_manifest"]["ok"] is True
    assert report["checks"]["snapshot_storage"]["ok"] is True


def test_internal_selftest_fails_closed_for_missing_manifest(tmp_path: Path):
    engine = create_engine("sqlite:///:memory:")
    report = run_internal_checks(
        engine=engine,
        manifest_path=tmp_path / "missing.yaml",
        snapshot_dir=tmp_path / "snapshots",
    )

    assert report["ok"] is False
    assert report["checks"]["source_manifest"]["ok"] is False
