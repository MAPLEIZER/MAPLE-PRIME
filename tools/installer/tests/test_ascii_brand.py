from kdr_installer.ascii_brand import ascii_logo_for_width


def test_ascii_logo_uses_full_mark_from_common_fullscreen_widths() -> None:
    compact = ascii_logo_for_width(100)
    assert "KENYA DATA RIGHTS" in compact
    assert len(compact.splitlines()) < 10

    art = ascii_logo_for_width(120)
    lines = art.splitlines()
    assert len(lines) >= 35
    assert max(map(len, lines)) <= 148
    assert "****" in art
