from kdr_installer.ascii_brand import ascii_logo_for_width


def test_standard_terminal_still_gets_visible_kdr_artwork() -> None:
    art = ascii_logo_for_width(100)
    assert art is not None
    assert "KENYA DATA RIGHTS" in art


def test_wide_terminal_gets_full_supplied_artwork() -> None:
    art = ascii_logo_for_width(180)
    assert art is not None
    assert len(art.splitlines()) > 20
