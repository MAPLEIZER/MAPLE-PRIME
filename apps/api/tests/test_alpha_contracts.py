from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.security import UnsafeOutboundURL, validate_outbound_url
from app.db.base import Base
from app.db.models import Institution, SourceSnapshot
from app.main import app
from app.services.sources import SourceManifest, load_manifest
from app.services.vault import VaultDecryptionError, decrypt_json, encrypt_json


def test_schema_metadata_has_named_core_tables() -> None:
    tables = set(Base.metadata.tables)
    assert {"institutions", "institution_aliases", "source_snapshots", "source_observations", "rights_requests", "audit_events"} <= tables
    assert Institution.__tablename__ == "institutions"
    assert SourceSnapshot.__tablename__ == "source_snapshots"


def test_source_manifest_rejects_unknown_scheme(tmp_path: Path) -> None:
    path = tmp_path / "sources.yaml"
    path.write_text("sources:\n  - id: evil\n    regulator: TEST\n    url: file:///etc/passwd\n    parser: html_table\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_manifest(path)


def test_source_manifest_loads_versioned_https_sources(tmp_path: Path) -> None:
    path = tmp_path / "sources.yaml"
    path.write_text("sources:\n  - id: cbk-dcp\n    regulator: CBK\n    url: https://www.centralbank.go.ke/example.pdf\n    parser: pdf_table\n    update_policy: manual\n", encoding="utf-8")
    manifest = load_manifest(path)
    assert isinstance(manifest, SourceManifest)
    assert manifest.sources[0].id == "cbk-dcp"


def test_outbound_url_policy_blocks_local_and_non_https_targets() -> None:
    for candidate in ["http://127.0.0.1/internal", "https://localhost/admin", "file:///etc/passwd", "ftp://example.com/file", "https://10.0.0.5/private", "https://169.254.169.254/latest/meta-data"]:
        with pytest.raises(UnsafeOutboundURL):
            validate_outbound_url(candidate)
    assert validate_outbound_url("https://www.centralbank.go.ke/") == "https://www.centralbank.go.ke/"


def test_vault_round_trip_and_tamper_detection() -> None:
    payload = {"full_name": "Test User", "phone": "+254700000000"}
    encrypted = encrypt_json(payload, "correct horse battery staple")
    assert payload["full_name"] not in encrypted
    assert decrypt_json(encrypted, "correct horse battery staple") == payload
    envelope = json.loads(encrypted)
    envelope["ciphertext"] = envelope["ciphertext"][:-3] + "AAA"
    with pytest.raises(VaultDecryptionError):
        decrypt_json(json.dumps(envelope), "correct horse battery staple")


def test_api_exposes_alpha_status_and_no_secret_values() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/health").json()["status"] == "ok"
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    body = response.json()
    assert body["release_stage"] == "alpha"
    assert "master_key" not in json.dumps(body).lower()
