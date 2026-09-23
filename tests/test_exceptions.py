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


def test_conversion_error_is_instantiable_without_arguments() -> None:
    exc = ConversionError()

    assert isinstance(exc, Exception)


def test_unsupported_file_error_stores_path() -> None:
    path = Path("input.pdf")

    exc = UnsupportedFileError(path)

    assert exc.path == path


def test_invalid_password_error_stores_path() -> None:
    path = Path("secret.pdf")

    exc = InvalidPasswordError(path)

    assert exc.path == path


def test_invalid_password_error_never_stores_a_password_value() -> None:
    exc = InvalidPasswordError(Path("secret.pdf"))

    assert "password" not in exc.__dict__


def test_corrupt_file_error_stores_path() -> None:
    path = Path("bad.pdf")

    exc = CorruptFileError(path)

    assert exc.path == path


@pytest.mark.parametrize(
    ("exc_type", "path"),
    [
        (UnsupportedFileError, Path("input.pdf")),
        (InvalidPasswordError, Path("input.pdf")),
        (CorruptFileError, Path("input.pdf")),
        (OutputWriteError, Path("output.md")),
    ],
)
def test_debug_message_includes_the_path(
    exc_type: type[ConversionError], path: Path
) -> None:
    exc = exc_type(path)

    assert str(path) in str(exc)


@pytest.mark.parametrize(
    "exc_type",
    [UnsupportedFileError, InvalidPasswordError, CorruptFileError, OutputWriteError],
)
def test_each_exception_can_be_caught_via_the_base_class(
    exc_type: type[ConversionError],
) -> None:
    with pytest.raises(ConversionError):
        raise exc_type(Path("input.pdf"))


def test_sibling_exception_types_are_not_interchangeable() -> None:
    try:
        raise UnsupportedFileError(Path("input.pdf"))
    except InvalidPasswordError:
        pytest.fail("UnsupportedFileError must not be catchable as InvalidPasswordError")
    except UnsupportedFileError:
        pass

    try:
        raise CorruptFileError(Path("input.pdf"))
    except OutputWriteError:
        pytest.fail("CorruptFileError must not be catchable as OutputWriteError")
    except CorruptFileError:
        pass


@pytest.mark.parametrize(
    "exc_type",
    [UnsupportedFileError, InvalidPasswordError, CorruptFileError, OutputWriteError],
)
def test_path_argument_is_required(exc_type: type[ConversionError]) -> None:
    with pytest.raises(TypeError):
        exc_type()


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
