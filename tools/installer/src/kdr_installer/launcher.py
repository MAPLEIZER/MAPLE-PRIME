from __future__ import annotations

import sys
from pathlib import Path

from kdr_installer.ascii_brand import ascii_logo_for_width
from kdr_installer import cli


def _install_branded_banner() -> None:
    original = cli._banner

    def branded_banner(root: Path) -> None:
        art = ascii_logo_for_width(cli.console.width)
        if art:
            cli.console.print(art, style="kdr.accent", highlight=False)
        original(root)

    cli._banner = branded_banner


def main() -> int:
    _install_branded_banner()
    return cli.main()


if __name__ == "__main__":
    sys.exit(main())
