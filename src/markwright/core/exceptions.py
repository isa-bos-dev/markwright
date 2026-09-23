from pathlib import Path


class ConversionError(Exception):
    """Base class for all domain-level conversion failures."""


class UnsupportedFileError(ConversionError):
    """Raised when the input file is missing, unreadable, or not a PDF."""

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(f"Unsupported or unreadable file: {path}")


class InvalidPasswordError(ConversionError):
    """Raised when a PDF is encrypted and the provided password is missing or wrong."""

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(f"Invalid or missing password for: {path}")


class CorruptFileError(ConversionError):
    """Raised when the PDF cannot be parsed due to corruption or an internal failure.

    Call sites should use ``raise CorruptFileError(path) from original_exc`` so the
    underlying cause is preserved via the standard ``__cause__`` chain instead of a
    custom attribute.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(f"Corrupt or unprocessable file: {path}")


class OutputWriteError(ConversionError):
    """Raised when the resulting Markdown or images cannot be written to disk.

    Call sites should use ``raise OutputWriteError(path) from original_exc``.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(f"Could not write output to: {path}")
