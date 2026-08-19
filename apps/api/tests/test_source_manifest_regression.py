from __future__ import annotations

from pathlib import Path

from app.services.sources import load_manifest

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_committed_source_manifest_parses_and_preserves_published_date_as_text() -> None:
    manifest = load_manifest(REPO_ROOT / "sources" / "source-manifest.yaml")
    cbk = next(source for source in manifest.sources if source.id == "cbk_dcp")
    assert cbk.published_at == "2026-07-09"
    assert len(manifest.sources) >= 2


def test_yaml_implicit_date_is_normalized_to_iso_text(tmp_path: Path) -> None:
    path = tmp_path / "sources.yaml"
    path.write_text(
        "sources:\n"
        "  cbk_dcp:\n"
        "    authority: Central Bank of Kenya\n"
        "    type: pdf\n"
        "    url: https://www.centralbank.go.ke/example.pdf\n"
        "    parser: cbk_dcp_pdf_v1\n"
        "    published_at: 2026-07-09\n",
        encoding="utf-8",
    )

    manifest = load_manifest(path)
    assert manifest.sources[0].published_at == "2026-07-09"
