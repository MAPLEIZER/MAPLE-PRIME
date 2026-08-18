from pathlib import Path

from kdr_installer.updates import (
    InstallerPreferences,
    UpdateMode,
    is_newer_release,
    load_preferences,
    parse_checksums,
    parse_version,
    release_asset_name,
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


def test_update_preferences_default_to_prompt_and_round_trip(tmp_path: Path) -> None:
    root = tmp_path / "kdr"
    assert load_preferences(root) == InstallerPreferences(update_mode=UpdateMode.PROMPT)

    save_preferences(root, InstallerPreferences(update_mode=UpdateMode.AUTO))
    assert load_preferences(root).update_mode is UpdateMode.AUTO
