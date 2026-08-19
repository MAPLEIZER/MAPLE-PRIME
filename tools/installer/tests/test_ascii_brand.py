from kdr_installer.ascii_brand import ascii_logo_for_width


def test_ascii_logo_uses_compact_mark_until_terminal_is_wide_enough() -> None:
    compact = ascii_logo_for_width(120)
    assert "KENYA DATA RIGHTS" in compact
    assert len(compact.splitlines()) < 10

    art = ascii_logo_for_width(160)
    lines = art.splitlines()
    assert len(lines) >= 35
    assert max(map(len, lines)) <= 148
    assert "****" in art
