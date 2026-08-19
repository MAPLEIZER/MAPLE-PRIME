from pathlib import Path

import pytest

from kdr_installer.updates import (
    InstallerPreferences,
    ReleaseInfo,
    UpdateMode,
    is_newer_release,
    load_preferences,
    managed_installer_path,
    parse_checksums,
    parse_version,
    release_asset_name,
    resolve_installer_asset,
    save_preferences,
)


def test_semantic_release_order_handles_alpha_and_stable_versions() -> None:
    assert parse_version("v0.1.0-alpha.2") > parse_version("0.1.0a1")
    assert parse_version("v0.1.0") > parse_version("v0.1.0-alpha.99")
    assert parse_version("v0.2.0-alpha.1") > parse_version("v0.1.99")
    assert is_newer_release("0.1.0a1", "v0.1.0-alpha.2")
    assert not is_newer_release("0.2.0", "v0.1.9")


def test_release_asset_names_are_explicit_per_supported_desktop_platform() -> None:
    assert release_asset_name("Windows", "AMD64") == "kdr-installer-windows-x86_64.exe"
    assert release_asset_name("Linux", "x86_64") == "kdr-installer-linux-x86_64"
    assert release_asset_name("Darwin", "arm64") == "kdr-installer-macos"


def test_checksum_manifest_parser_accepts_only_sha256_lines() -> None:
    parsed = parse_checksums(
        "a" * 64 + "  kdr-installer-linux-x86_64\n" + "not-a-checksum file\n"
    )
    assert parsed == {"kdr-installer-linux-x86_64": "a" * 64}


def test_resolve_installer_asset_requires_release_asset_and_checksum() -> None:
    release = ReleaseInfo(
        tag="alpha-latest",
        source_sha="a" * 40,
        html_url="https://github.com/MAPLEIZER/kenya-data-rights/releases/tag/alpha-latest",
        published_at=None,
        assets={
            "kdr-installer-macos": "https://github.com/example/kdr-installer-macos",
            "SHA256SUMS.txt": "https://github.com/example/SHA256SUMS.txt",
        },
    )
    resolved = resolve_installer_asset(release, "b" * 64 + "  kdr-installer-macos\n", system="Darwin", machine="arm64")
    assert resolved.name == "kdr-installer-macos"
    assert resolved.sha256 == "b" * 64

    with pytest.raises(ValueError):
        resolve_installer_asset(release, "", system="Darwin", machine="arm64")


def test_managed_installer_path_is_inside_private_kdr_config(tmp_path: Path) -> None:
    root = tmp_path / "KDR"
    assert managed_installer_path(root, system="Darwin").parent == root / ".kdr" / "bin"
    assert managed_installer_path(root, system="Windows").suffix == ".exe"


def test_update_preferences_default_to_prompt_and_round_trip(tmp_path: Path) -> None:
    root = tmp_path / "kdr"
    assert load_preferences(root) == InstallerPreferences(update_mode=UpdateMode.PROMPT)

    save_preferences(root, InstallerPreferences(update_mode=UpdateMode.AUTO))
    assert load_preferences(root).update_mode is UpdateMode.AUTO
