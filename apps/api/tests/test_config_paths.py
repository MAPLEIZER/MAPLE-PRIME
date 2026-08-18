from pathlib import Path

from app.core.config import discover_project_root


def test_project_root_discovery_handles_shallow_container_layout(tmp_path: Path) -> None:
    module_file = tmp_path / "app" / "core" / "config.py"
    module_file.parent.mkdir(parents=True)
    module_file.write_text("", encoding="utf-8")

    assert discover_project_root(module_file) == tmp_path


def test_project_root_discovery_prefers_ancestor_with_source_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "sources" / "source-manifest.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("sources: {}\n", encoding="utf-8")
    module_file = tmp_path / "apps" / "api" / "app" / "core" / "config.py"
    module_file.parent.mkdir(parents=True)
    module_file.write_text("", encoding="utf-8")

    assert discover_project_root(module_file) == tmp_path
