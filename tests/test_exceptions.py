from pathlib import Path

import pytest

from markwright.core.exceptions import (
    ConversionError,
    CorruptFileError,
    InvalidPasswordError,
    OutputWriteError,
    UnsupportedFileError,
)


@pytest.mark.parametrize(
    "exc",
    [
        UnsupportedFileError(Path("input.pdf")),
        InvalidPasswordError(Path("input.pdf")),
        CorruptFileError(Path("input.pdf")),
        OutputWriteError(Path("output.md")),
    ],
)
def test_all_domain_exceptions_inherit_from_conversion_error(exc: ConversionError) -> None:
    assert isinstance(exc, ConversionError)
    assert isinstance(exc, Exception)


def test_unsupported_file_error_stores_path() -> None:
    path = Path("input.pdf")

    exc = UnsupportedFileError(path)

    assert exc.path == path


def test_invalid_password_error_never_stores_a_password_value() -> None:
    exc = InvalidPasswordError(Path("secret.pdf"))

    assert "password" not in exc.__dict__


def test_corrupt_file_error_chains_the_original_cause() -> None:
    original = ValueError("boom")

    try:
        raise CorruptFileError(Path("bad.pdf")) from original
    except CorruptFileError as exc:
        assert exc.__cause__ is original


def test_output_write_error_stores_path_and_chains_cause() -> None:
    original = OSError("disk full")

    try:
        raise OutputWriteError(Path("output.md")) from original
    except OutputWriteError as exc:
        assert exc.path == Path("output.md")
        assert exc.__cause__ is original
