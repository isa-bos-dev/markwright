import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Single entry point: a file runs the CLI; "menu" or no arguments at all
    open the interactive menu — the effortless, no-setup-needed entry point
    (the desktop GUI is parked on the `gui-desktop` branch, not built here).
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] != "menu":
        from markwright.cli.cli import run as run_cli

        return run_cli(arguments)

    from markwright.cli.menu import run_menu

    return run_menu(arguments[1:])  # [] both with no arguments and with "menu" alone
