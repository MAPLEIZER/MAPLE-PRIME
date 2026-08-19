from pathlib import Path

import pytest

from kdr_installer.core import (
    InstallAction,
    SelfTestCheck,
    compose_args,
    default_install_root,
    installer_menu,
    self_test_plan,
)


def test_install_root_is_user_scoped_and_not_repository_relative(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("KDR_INSTALL_HOME", str(tmp_path / "kdr-home"))
    root = default_install_root()
    assert root == tmp_path / "kdr-home"
    assert not root.is_absolute() or str(root).startswith(str(tmp_path))


def test_compose_commands_are_argument_vectors_and_preserve_data_by_default():
    start = compose_args(InstallAction.START)
    update = compose_args(InstallAction.UPDATE)
    repair = compose_args(InstallAction.REPAIR)
    uninstall = compose_args(InstallAction.UNINSTALL)
    purge = compose_args(InstallAction.UNINSTALL, purge_data=True)

    assert start[:2] == ["docker", "compose"]
    assert "up" in start and "-d" in start
    assert "--force-recreate" in update
    assert "--force-recreate" in repair
    assert uninstall[-1] == "down"
    assert "-v" not in uninstall
    assert purge[-2:] == ["down", "-v"]


def test_self_test_plan_covers_the_whole_local_user_path():
    checks = set(self_test_plan())
    assert {
        SelfTestCheck.DOCKER_CLI,
        SelfTestCheck.DOCKER_DAEMON,
        SelfTestCheck.COMPOSE,
        SelfTestCheck.API_DIRECT,
        SelfTestCheck.WEB,
        SelfTestCheck.API_PROXY,
        SelfTestCheck.API_INTERNAL,
        SelfTestCheck.PERSISTENCE,
    }.issubset(checks)


def test_menu_exposes_diagnostics_install_sync_repair_self_test_and_safe_uninstall():
    actions = [item.action for item in installer_menu()]
    assert actions[:5] == [
        InstallAction.INSTALL,
        InstallAction.START,
        InstallAction.SELF_TEST,
        InstallAction.SUPPORT_BUNDLE,
        InstallAction.SYNC_SOURCES,
    ]
    assert InstallAction.REPAIR in actions
    assert InstallAction.OPEN in actions
    assert InstallAction.UNINSTALL in actions
    assert actions[-1] == InstallAction.QUIT


def test_unknown_action_is_not_convertible_to_compose_command():
    with pytest.raises(ValueError):
        compose_args(InstallAction.OPEN)
