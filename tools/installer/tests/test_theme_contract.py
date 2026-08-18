from kdr_installer.theme import KDR_THEME, THEME_ROLES


def test_theme_has_semantic_roles_for_tui_states():
    assert {
        "kdr.title",
        "kdr.accent",
        "kdr.success",
        "kdr.warning",
        "kdr.danger",
        "kdr.muted",
    }.issubset(THEME_ROLES)
    for role in THEME_ROLES:
        assert role in KDR_THEME.styles
