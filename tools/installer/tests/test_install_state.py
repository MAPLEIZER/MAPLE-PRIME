from pathlib import Path

from kdr_installer.updates import InstallState, load_install_state, save_install_state


def test_install_state_round_trip_tracks_exact_source_commit(tmp_path: Path) -> None:
    state = InstallState(
        source_sha="a" * 40,
        release_tag="alpha-latest",
        installed_version="0.1.0a1",
    )
    save_install_state(tmp_path, state)
    assert load_install_state(tmp_path) == state


def test_install_state_is_separate_from_docker_data(tmp_path: Path) -> None:
    save_install_state(tmp_path, InstallState(source_sha="b" * 40))
    assert (tmp_path / ".kdr" / "install-state.json").is_file()
