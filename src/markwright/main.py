import sys
from collections.abc import Sequence

from markwright.i18n import DEFAULT_LANGUAGE, t

EXIT_GUI_UNAVAILABLE = 69


def main(argv: Sequence[str] | None = None) -> int:
    """Single entry point: with arguments run the CLI, without them open the GUI.

    Each mode is imported only when used, so the CLI never loads tkinter and
    neither mode pays for the other's start-up cost.
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
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
