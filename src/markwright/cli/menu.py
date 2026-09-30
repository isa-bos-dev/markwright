import argparse
from collections.abc import Sequence
from pathlib import Path

import pyfiglet
from rich.console import Console
from rich.markup import escape
from rich.prompt import Prompt

from markwright import APP_NAME
from markwright.cli.cli import (
    EXIT_CODE_BY_EXCEPTION,
    EXIT_SUCCESS,
    EXIT_UNEXPECTED_ERROR,
    print_domain_error,
    print_progress,
    print_unexpected_error,
)
from markwright.core.converter import ConversionStage, ConversionWarning, convert_pdf_to_md
from markwright.core.exceptions import ConversionError, InvalidPasswordError
from markwright.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, t
from markwright.i18n.errors import ERROR_MESSAGE_KEYS


def find_pdfs(directory: Path) -> list[Path]:
    """Every ``.pdf`` file directly inside ``directory`` (not recursive), by name."""
    return sorted(
        (path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".pdf"),
        key=lambda path: path.name.lower(),
    )


def sanitize_for_terminal(text: str) -> str:
    """Make ``text`` (e.g. a filename from disk) safe to print as-is.

    Strips non-printable control characters (which could otherwise carry raw
    ANSI escape sequences) and escapes rich's own markup syntax, so a
    maliciously named file cannot alter what the terminal shows (TUI-FR-007).
    """
    printable = "".join(character for character in text if character.isprintable())
    return escape(printable)


def resolve_choice(raw: str, pdfs: list[Path]) -> Path:
    """The picked PDF (a number from the list) or the typed text as a path.

    An out-of-range number falls through to being treated as a literal path,
    which the normal "unsupported file" handling already reports clearly —
    no separate "invalid number" error is needed.
    """
    raw = raw.strip()
    if raw.isdigit():
        index = int(raw) - 1
        if 0 <= index < len(pdfs):
            return pdfs[index]
    return Path(raw)


def _parse_lang(argv: Sequence[str] | None) -> str:
    parser = argparse.ArgumentParser(
        prog="markwright menu",
        description=(
            "Pick a PDF from the current folder's numbered list (or type a path) "
            "and convert it, without typing the full path yourself."
        ),
    )
    parser.add_argument(
        "--lang",
        choices=list(SUPPORTED_LANGUAGES),
        default=DEFAULT_LANGUAGE,
        help="Interface language.",
    )
    return str(parser.parse_args(argv).lang)


_BANNER_COLOR = "#4A90E2"  # the brand blue used across the logo, README badges and GUI.

_MENU_CONVERT = "1"
_MENU_HELP = "2"
_MENU_LANGUAGE = "3"
_MENU_QUIT = "4"
_MENU_CHOICES = (_MENU_CONVERT, _MENU_HELP, _MENU_LANGUAGE, _MENU_QUIT)


def _print_banner(console: Console, lang: str) -> None:
    art = pyfiglet.figlet_format(APP_NAME, font="small")
    console.print(f"[bold {_BANNER_COLOR}]{art}[/bold {_BANNER_COLOR}]", end="")
    console.print(t("main.subtitle", lang), style="dim")


def _print_main_menu(console: Console, lang: str) -> None:
    other_language = next(code for code in SUPPORTED_LANGUAGES if code != lang)
    console.print()
    console.print(f"  [bold]{_MENU_CONVERT}.[/bold] {t('menu.option_convert', lang)}")
    console.print(f"  [bold]{_MENU_HELP}.[/bold] {t('menu.option_help', lang)}")
    console.print(
        f"  [bold]{_MENU_LANGUAGE}.[/bold] "
        f"{t('menu.option_language', lang, language=SUPPORTED_LANGUAGES[other_language])}"
    )
    console.print(f"  [bold]{_MENU_QUIT}.[/bold] {t('menu.option_quit', lang)}")


def _convert_one(console: Console, lang: str, cwd: Path) -> int:
    """Pick one PDF (from the list or a typed path) and convert it; return its exit code."""
    pdfs = find_pdfs(cwd)
    if pdfs:
        console.print(t("menu.found_pdfs", lang))
        for index, pdf in enumerate(pdfs, start=1):
            console.print(f"  {index}. {sanitize_for_terminal(pdf.name)}")
        raw = Prompt.ask(t("menu.choose_prompt", lang))
    else:
        console.print(t("menu.no_pdfs_found", lang))
        raw = Prompt.ask(t("menu.type_path_prompt", lang))

    input_path = resolve_choice(raw, pdfs)

    def on_progress(stage: ConversionStage, warning: ConversionWarning | None = None) -> None:
        print_progress(stage, warning, lang)

    password: str | None = None
    while True:
        try:
            output_path = convert_pdf_to_md(input_path, password=password, on_progress=on_progress)
        except InvalidPasswordError:
            password = Prompt.ask(t("main.password", lang), password=True)
            continue
        except ConversionError as exc:
            message_key = ERROR_MESSAGE_KEYS.get(type(exc), "error.unexpected")
            print_domain_error(exc, message_key, lang, verbose=False)
            return EXIT_CODE_BY_EXCEPTION.get(type(exc), EXIT_UNEXPECTED_ERROR)
        except Exception as exc:  # noqa: BLE001 - mirrors cli.run's deliberate catch-all
            print_unexpected_error(exc, verbose=False)
            return EXIT_UNEXPECTED_ERROR
        else:
            console.print(sanitize_for_terminal(str(output_path)))
            return EXIT_SUCCESS


def run_menu(argv: Sequence[str] | None = None) -> int:
    """Interactive loop: a real menu (convert / help / language / quit), not a
    single yes-or-no prompt (TUI-FR-001)."""
    lang = _parse_lang(argv)
    console = Console()
    exit_code = EXIT_SUCCESS
    try:
        while True:
            _print_banner(console, lang)
            _print_main_menu(console, lang)
            choice = Prompt.ask(t("menu.prompt_choice", lang), choices=list(_MENU_CHOICES))
            if choice == _MENU_QUIT:
                return exit_code
            if choice == _MENU_HELP:
                console.print()
                console.print(t("menu.help_text", lang))
            elif choice == _MENU_LANGUAGE:
                lang = next(code for code in SUPPORTED_LANGUAGES if code != lang)
            elif choice == _MENU_CONVERT:
                exit_code = _convert_one(console, lang, Path.cwd())
    except KeyboardInterrupt:
        console.print()
        return EXIT_SUCCESS
