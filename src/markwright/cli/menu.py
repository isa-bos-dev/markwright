from pathlib import Path

from rich.markup import escape


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
