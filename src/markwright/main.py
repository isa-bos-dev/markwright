import sys
from collections.abc import Sequence

from markwright.i18n import DEFAULT_LANGUAGE, t

EXIT_GUI_UNAVAILABLE = 69


def main(argv: Sequence[str] | None = None) -> int:
    """Single entry point: CLI with a file, interactive menu with "menu", else the GUI.

    Each mode is imported only when used, so no mode pays for another's start-up
    cost (the CLI and the menu never load tkinter; the GUI never loads `rich`).
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "menu":
        from markwright.cli.menu import run_menu

        return run_menu(arguments[1:])
    if arguments:
        from markwright.cli.cli import run as run_cli

        return run_cli(arguments)
    return _run_gui()


def _run_gui() -> int:
    try:
        from markwright.gui.gui import run as run_gui
    except ImportError as error:  # tkinter is not installed
        return _report_gui_unavailable(error)

    from tkinter import TclError

    try:
        run_gui()
    except TclError as error:  # e.g. no display available
        return _report_gui_unavailable(error)
    return 0


def _report_gui_unavailable(error: Exception) -> int:
    reason = (str(error).splitlines() or [type(error).__name__])[0]
    print(t("error.gui_unavailable", DEFAULT_LANGUAGE, reason=reason), file=sys.stderr)
    return EXIT_GUI_UNAVAILABLE
