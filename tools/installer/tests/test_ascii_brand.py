from kdr_installer.ascii_brand import ascii_logo_for_width


def test_ascii_logo_uses_full_mark_only_when_terminal_is_wide_enough() -> None:
    assert ascii_logo_for_width(120) is None
    art = ascii_logo_for_width(160)
    assert art is not None
    lines = art.splitlines()
    assert len(lines) >= 35
    assert max(map(len, lines)) <= 148
    assert "****" in art
