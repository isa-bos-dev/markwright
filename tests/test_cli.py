from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from markwright.cli.cli import (
    EXIT_CORRUPT_FILE,
    EXIT_INVALID_PASSWORD,
    EXIT_OUTPUT_WRITE_FAILED,
    EXIT_SUCCESS,
    EXIT_UNEXPECTED_ERROR,
    EXIT_UNSUPPORTED_FILE,
    run,
)
from markwright.core.converter import ConversionStage, ConversionWarning
from markwright.core.exceptions import (
    CorruptFileError,
    InvalidPasswordError,
    OutputWriteError,
    UnsupportedFileError,
)


@pytest.fixture
def mock_convert(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    import markwright.cli.cli as cli_module

    mock = MagicMock()
    monkeypatch.setattr(cli_module, "convert_pdf_to_md", mock)
    return mock


def _progress_emitting_convert(
    *stages: ConversionStage | tuple[ConversionStage, ConversionWarning],
    result: Path = Path("/tmp/report.md"),
) -> Callable[..., Path]:
    def _fake(input_path, output_path=None, password=None, on_progress=None) -> Path:
        for item in stages:
            if isinstance(item, tuple):
                on_progress(*item)
            else:
                on_progress(item)
        return result

    return _fake


# --- Success cases ---


def test_successful_conversion_prints_output_path_and_returns_zero(
    mock_convert: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    mock_convert.return_value = Path("/tmp/report.md")

    exit_code = run(["report.pdf"])

    captured = capsys.readouterr()
    assert exit_code == EXIT_SUCCESS
    assert "report.md" in captured.out


def test_quiet_suppresses_progress_but_still_prints_output_path(
    mock_convert: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    mock_convert.side_effect = _progress_emitting_convert(
        ConversionStage.STARTED, ConversionStage.DONE
    )

    exit_code = run(["report.pdf", "--quiet"])

    captured = capsys.readouterr()
    assert exit_code == EXIT_SUCCESS
    assert "report.md" in captured.out
    assert "Starting" not in captured.out
    assert "Starting" not in captured.err


def test_progress_messages_are_printed_without_quiet(
    mock_convert: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    mock_convert.side_effect = _progress_emitting_convert(
        ConversionStage.STARTED,
        ConversionStage.CONVERTING,
        ConversionStage.WRITING,
        ConversionStage.DONE,
    )

    run(["report.pdf"])

    captured = capsys.readouterr()
    assert "Starting conversion" in captured.out
    assert "Converting PDF" in captured.out
    assert "Saving result" in captured.out
    assert "Conversion complete" in captured.out


def test_lang_es_prints_progress_in_spanish(
    mock_convert: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    mock_convert.side_effect = _progress_emitting_convert(ConversionStage.STARTED)

    run(["report.pdf", "--lang", "es"])

    captured = capsys.readouterr()
    assert "Iniciando conversión" in captured.out


def test_default_language_is_english(
    mock_convert: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    mock_convert.side_effect = _progress_emitting_convert(ConversionStage.STARTED)

    run(["report.pdf"])

    captured = capsys.readouterr()
    assert "Starting conversion" in captured.out


def test_output_flag_is_forwarded_to_core(mock_convert: MagicMock) -> None:
    mock_convert.return_value = Path("/tmp/custom.md")

    run(["report.pdf", "-o", "/tmp/custom.md"])

    _, kwargs = mock_convert.call_args
    assert kwargs["output_path"] == "/tmp/custom.md"


def test_password_flag_is_forwarded_to_core(mock_convert: MagicMock) -> None:
    mock_convert.return_value = Path("/tmp/report.md")

    run(["report.pdf", "--password", "secret123"])

    _, kwargs = mock_convert.call_args
    assert kwargs["password"] == "secret123"


def test_partial_success_retryable_prints_matching_message_even_with_quiet(
    mock_convert: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    warning = ConversionWarning(retryable=True, categories=("timeout",), affected_pages=(2,))
    mock_convert.side_effect = _progress_emitting_convert(
        (ConversionStage.PARTIAL_SUCCESS, warning)
    )

    exit_code = run(["report.pdf", "--quiet"])

    captured = capsys.readouterr()
    assert exit_code == EXIT_SUCCESS
    assert "try again" in captured.err


def test_partial_success_not_retryable_prints_matching_message(
    mock_convert: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    warning = ConversionWarning(
        retryable=False, categories=("backend_failure",), affected_pages=(1,)
    )
    mock_convert.side_effect = _progress_emitting_convert(
        (ConversionStage.PARTIAL_SUCCESS, warning)
    )

    run(["report.pdf"])

    captured = capsys.readouterr()
    assert "content of those pages" in captured.err


# --- Error cases ---


@pytest.mark.parametrize(
    ("exc_type", "expected_exit_code"),
    [
        (UnsupportedFileError, EXIT_UNSUPPORTED_FILE),
        (InvalidPasswordError, EXIT_INVALID_PASSWORD),
        (CorruptFileError, EXIT_CORRUPT_FILE),
        (OutputWriteError, EXIT_OUTPUT_WRITE_FAILED),
    ],
)
def test_domain_exceptions_map_to_specific_exit_codes(
    mock_convert: MagicMock,
    capsys: pytest.CaptureFixture[str],
    exc_type: type[Exception],
    expected_exit_code: int,
) -> None:
    mock_convert.side_effect = exc_type(Path("report.pdf"))

    exit_code = run(["report.pdf"])

    captured = capsys.readouterr()
    assert exit_code == expected_exit_code
    assert captured.err != ""


def test_unexpected_error_without_verbose_shows_generic_message_and_no_traceback(
    mock_convert: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    mock_convert.side_effect = RuntimeError("bug!")

    exit_code = run(["report.pdf"])

    captured = capsys.readouterr()
    assert exit_code == EXIT_UNEXPECTED_ERROR
    assert "unexpected error" in captured.err.lower()
    assert "Traceback" not in captured.err


def test_unexpected_error_with_verbose_shows_traceback(
    mock_convert: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    mock_convert.side_effect = RuntimeError("bug!")

    exit_code = run(["report.pdf", "--verbose"])

    captured = capsys.readouterr()
    assert exit_code == EXIT_UNEXPECTED_ERROR
    assert "Traceback" in captured.err


def test_verbose_shows_the_technical_cause_of_a_domain_error(
    mock_convert: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    error = CorruptFileError(Path("report.pdf"))
    error.__cause__ = ValueError("parser exploded")
    mock_convert.side_effect = error

    run(["report.pdf", "--verbose"])

    error_output = capsys.readouterr().err
    assert "[debug]" in error_output
    assert "parser exploded" in error_output


def test_technical_details_are_hidden_without_verbose(
    mock_convert: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    error = CorruptFileError(Path("report.pdf"))
    error.__cause__ = ValueError("parser exploded")
    mock_convert.side_effect = error

    run(["report.pdf"])

    error_output = capsys.readouterr().err
    assert "[debug]" not in error_output
    assert "parser exploded" not in error_output


def test_unsupported_language_is_rejected_by_argparse(
    mock_convert: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        run(["report.pdf", "--lang", "fr"])

    assert exc_info.value.code == 2
    assert "invalid choice" in capsys.readouterr().err
    mock_convert.assert_not_called()


def test_password_never_appears_in_any_printed_output(
    mock_convert: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    mock_convert.side_effect = InvalidPasswordError(Path("report.pdf"))

    run(["report.pdf", "--password", "super-secret-value", "--verbose"])

    captured = capsys.readouterr()
    assert "super-secret-value" not in captured.out
    assert "super-secret-value" not in captured.err
