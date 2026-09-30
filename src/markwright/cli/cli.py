import argparse
import sys
import traceback
from collections.abc import Sequence

from markwright import APP_NAME, get_version
from markwright.core.converter import ConversionStage, ConversionWarning, convert_pdf_to_md
from markwright.core.exceptions import (
    ConversionError,
    CorruptFileError,
    InvalidPasswordError,
    OutputWriteError,
    UnsupportedFileError,
)
from markwright.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, t
from markwright.i18n.errors import ERROR_MESSAGE_KEYS

EXIT_SUCCESS = 0
EXIT_UNSUPPORTED_FILE = 1
EXIT_INVALID_PASSWORD = 2
EXIT_CORRUPT_FILE = 3
EXIT_OUTPUT_WRITE_FAILED = 4
EXIT_UNEXPECTED_ERROR = 70

EXIT_CODE_BY_EXCEPTION: dict[type[ConversionError], int] = {
    UnsupportedFileError: EXIT_UNSUPPORTED_FILE,
    InvalidPasswordError: EXIT_INVALID_PASSWORD,
    CorruptFileError: EXIT_CORRUPT_FILE,
    OutputWriteError: EXIT_OUTPUT_WRITE_FAILED,
}


def print_progress(
    stage: ConversionStage, warning: ConversionWarning | None, lang: str, quiet: bool = False
) -> None:
    """Print one progress update, shared by the CLI and the interactive menu."""
    if stage == ConversionStage.PARTIAL_SUCCESS:
        key = (
            "progress.partial_success.retryable"
            if warning is not None and warning.retryable
            else "progress.partial_success.not_retryable"
        )
        print(t(key, lang), file=sys.stderr)
        return
    if not quiet:
        print(t(f"progress.{stage.value}", lang))


_EPILOG = """\
Examples:
  markwright report.pdf                 Convert report.pdf to report.md
  markwright report.pdf -o out.md       Choose the output filename
  markwright report.pdf --lang es       Progress messages in Spanish
  markwright secret.pdf --password ***  Decrypt a protected PDF
  markwright                            Open the graphical interface
  markwright menu                       Pick a PDF from the current folder, interactively
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markwright",
        description=(
            "Convert a PDF file to Markdown. Run with no arguments to open the\n"
            "graphical interface instead, or `markwright menu` for an interactive\n"
            "terminal menu that picks a PDF without typing its full path."
        ),
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"{APP_NAME} {get_version()}",
    )
    parser.add_argument("input_path", help="Path to the PDF file to convert.")
    parser.add_argument(
        "-o",
        "--output",
        dest="output_path",
        default=None,
        help="Destination path for the generated Markdown file.",
    )
    parser.add_argument(
        "--lang",
        choices=list(SUPPORTED_LANGUAGES),
        default=DEFAULT_LANGUAGE,
        help="Interface language.",
    )
    parser.add_argument(
        "--password",
        default=None,
        help=(
            "Password for a protected PDF. Warning: this may remain visible in "
            "your shell history; prefer running without this flag if that is a "
            "concern."
        ),
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress progress messages.")
    parser.add_argument(
        "--verbose", action="store_true", help="Show technical error details for debugging."
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    lang = args.lang

    def on_progress(stage: ConversionStage, warning: ConversionWarning | None = None) -> None:
        print_progress(stage, warning, lang, args.quiet)

    try:
        output_path = convert_pdf_to_md(
            args.input_path,
            output_path=args.output_path,
            password=args.password,
            on_progress=on_progress,
        )
    except ConversionError as exc:
        message_key = ERROR_MESSAGE_KEYS.get(type(exc), "error.unexpected")
        print_domain_error(exc, message_key, lang, args.verbose)
        return EXIT_CODE_BY_EXCEPTION.get(type(exc), EXIT_UNEXPECTED_ERROR)
    except Exception as exc:  # noqa: BLE001 - deliberate catch-all, see print_unexpected_error
        print_unexpected_error(exc, args.verbose)
        return EXIT_UNEXPECTED_ERROR

    print(output_path)
    return EXIT_SUCCESS


def print_domain_error(exc: ConversionError, message_key: str, lang: str, verbose: bool) -> None:
    """Print a localized error message, shared by the CLI and the interactive menu."""
    path = getattr(exc, "path", "")
    print(t(message_key, lang, path=path), file=sys.stderr)
    if verbose:
        print(f"\n[debug] {exc!r}", file=sys.stderr)
        if exc.__cause__ is not None:
            print(f"[debug] caused by: {exc.__cause__!r}", file=sys.stderr)


def print_unexpected_error(exc: Exception, verbose: bool) -> None:
    if verbose:
        traceback.print_exception(type(exc), exc, exc.__traceback__)
    else:
        print(t("error.unexpected"), file=sys.stderr)
