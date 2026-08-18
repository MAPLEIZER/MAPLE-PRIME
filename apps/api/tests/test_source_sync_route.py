from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.api.routes as routes
from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.services.fetcher import SourceFetchError


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _manifest(tmp_path: Path) -> Path:
    path = tmp_path / "sources.yaml"
    path.write_text(
        "sources:\n"
        "  cbk_dcp:\n"
        "    authority: Central Bank of Kenya\n"
        "    type: pdf\n"
        "    url: https://www.centralbank.go.ke/example.pdf\n"
        "    parser: cbk_dcp_pdf_v1\n",
        encoding="utf-8",
    )
    return path


def _settings(manifest: Path, tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        source_manifest_path=str(manifest),
        snapshot_dir=str(tmp_path / "snapshots"),
    )


def test_sync_endpoint_requires_local_action_header(tmp_path: Path, monkeypatch) -> None:
    manifest = _manifest(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: _settings(manifest, tmp_path))
    with _session() as session:
        app.dependency_overrides[get_session] = lambda: session
        try:
            response = TestClient(app).post("/api/v1/sources/cbk_dcp/sync")
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()


def test_sync_endpoint_runs_only_manifest_source(tmp_path: Path, monkeypatch) -> None:
    manifest = _manifest(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: _settings(manifest, tmp_path))
    monkeypatch.setattr(
        routes,
        "sync_source",
        lambda source, **_: SimpleNamespace(
            source_id=source.id,
            snapshot_id="snapshot-1",
            sha256="a" * 64,
            record_count=252,
            content_path=tmp_path / "snapshot.pdf",
        ),
    )

    with _session() as session:
        app.dependency_overrides[get_session] = lambda: session
        client = TestClient(app)
        try:
            missing = client.post(
                "/api/v1/sources/not-real/sync",
                headers={"X-KDR-Local-Action": "sync"},
            )
            assert missing.status_code == 404

            response = client.post(
                "/api/v1/sources/cbk_dcp/sync",
                headers={"X-KDR-Local-Action": "sync"},
            )
            assert response.status_code == 200
            assert response.json()["record_count"] == 252
            assert response.json()["source_id"] == "cbk_dcp"
        finally:
            app.dependency_overrides.clear()


def test_known_sync_failure_does_not_expose_internal_error_detail(tmp_path: Path, monkeypatch) -> None:
    manifest = _manifest(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: _settings(manifest, tmp_path))

    def fail_sync(*_, **__):
        raise SourceFetchError("secret upstream parser/network detail")

    monkeypatch.setattr(routes, "sync_source", fail_sync)

    with _session() as session:
        app.dependency_overrides[get_session] = lambda: session
        try:
            response = TestClient(app).post(
                "/api/v1/sources/cbk_dcp/sync",
                headers={"X-KDR-Local-Action": "sync"},
            )
            assert response.status_code == 502
            assert response.json()["detail"] == {
                "source_id": "cbk_dcp",
                "code": "source_fetch_failed",
                "message": "KDR could not download the official source.",
            }
            assert "secret" not in response.text.lower()
        finally:
            app.dependency_overrides.clear()
