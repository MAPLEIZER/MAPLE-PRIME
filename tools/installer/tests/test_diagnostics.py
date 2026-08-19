from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path

from kdr_installer.diagnostics import export_support_bundle, redact_text


def test_redaction_removes_mobile_and_bearer_secrets() -> None:
    text = (
        "KDR_MOBILE_API_TOKEN=super-secret-token\n"
        "Authorization: Bearer abc.def.ghi\n"
        '"pairing_token": "pair-me-123"\n'
    )
    redacted = redact_text(text)
    assert "super-secret-token" not in redacted
    assert "abc.def.ghi" not in redacted
    assert "pair-me-123" not in redacted
    assert "<redacted>" in redacted


def test_support_bundle_contains_only_sanitized_diagnostics(tmp_path: Path) -> None:
    root = tmp_path / "KenyaDataRights"
    (root / ".kdr" / "logs").mkdir(parents=True)
    (root / ".kdr" / "logs" / "installer.log").write_text(
        "startup ok KDR_MOBILE_API_TOKEN=never-share-this\n",
        encoding="utf-8",
    )
    (root / ".kdr" / "install-state.json").write_text(
        json.dumps({"source_sha": "a" * 40, "release_tag": "alpha-latest", "installed_version": "0.1.0a5"}),
        encoding="utf-8",
    )
    compose = root / "deploy" / "docker-compose" / "compose.yaml"
    compose.parent.mkdir(parents=True)
    compose.write_text("name: kenya-data-rights\n", encoding="utf-8")

    def fake_runner(args, *, cwd=None, check=False):
        joined = " ".join(str(value) for value in args)
        return subprocess.CompletedProcess(args, 0, stdout=f"ok {joined}\nAuthorization: Bearer should-hide\n", stderr="")

    bundle = export_support_bundle(
        root,
        output_dir=tmp_path,
        runner=fake_runner,
        selftest_loader=lambda: {
            "ok": False,
            "checks": {
                "source_manifest": {
                    "ok": False,
                    "detail": "manifest parse failed",
                    "path": "/app/sources/source-manifest.yaml",
                    "sha256": "b" * 64,
                    "error_type": "ValidationError",
                }
            },
        },
    )

    assert bundle.suffix == ".zip"
    with zipfile.ZipFile(bundle) as archive:
        names = set(archive.namelist())
        assert {
            "summary.json",
            "self-test.json",
            "docker-version.txt",
            "compose-version.txt",
            "compose-ps.txt",
            "api-logs.txt",
            "web-logs.txt",
            "api-data-init-logs.txt",
            "container-manifest.txt",
            "installer.log",
        }.issubset(names)
        all_text = "\n".join(archive.read(name).decode("utf-8", errors="replace") for name in names)

    assert "never-share-this" not in all_text
    assert "should-hide" not in all_text
    assert "<redacted>" in all_text
    assert "ValidationError" in all_text
