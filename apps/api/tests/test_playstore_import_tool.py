import json
import subprocess
import sys
from pathlib import Path


def test_play_export_normalizer_accepts_common_scraper_field_names(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    script = root / "tools" / "playstore-import" / "normalize_export.py"
    source = tmp_path / "apps.json"
    source.write_text(
        json.dumps(
            [
                {
                    "appId": "ke.co.example.cash",
                    "title": "Example Cash",
                    "developer": "Example Credit Limited",
                    "developerEmail": "SUPPORT@EXAMPLE.CO.KE",
                    "developerWebsite": "https://example.co.ke",
                    "privacyPolicy": "https://example.co.ke/privacy",
                    "url": "https://play.google.com/store/apps/details?id=ke.co.example.cash",
                    "genre": "Finance",
                    "installs": "10,000+",
                }
            ]
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            str(source),
            "--source-provider",
            "fixture-scraper",
            "--source-url",
            "https://example.invalid/export/123",
            "--observed-at",
            "2026-08-19T10:00:00+00:00",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert len(payload["records"]) == 1
    row = payload["records"][0]
    assert row["package_name"] == "ke.co.example.cash"
    assert row["support_email"] == "support@example.co.ke"
    assert row["developer_website"] == "https://example.co.ke"
    assert row["source_provider"] == "fixture-scraper"
    assert row["source_url"] == "https://example.invalid/export/123"


def test_play_export_normalizer_rejects_rows_without_package_identity(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    script = root / "tools" / "playstore-import" / "normalize_export.py"
    source = tmp_path / "bad.json"
    source.write_text(json.dumps([{"title": "Mystery Loan"}]), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(script), str(source), "--source-provider", "fixture"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "package" in result.stderr.lower()
