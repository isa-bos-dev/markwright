from pathlib import Path
from unittest.mock import MagicMock

import pytest

import markwright.cli.menu as menu_module
from markwright.cli.cli import EXIT_CORRUPT_FILE, EXIT_SUCCESS
from markwright.cli.menu import find_pdfs, resolve_choice, run_menu, sanitize_for_terminal
from markwright.core.exceptions import CorruptFileError, InvalidPasswordError

# --- find_pdfs ---


def test_finds_every_pdf_in_the_directory_sorted_by_name(tmp_path: Path) -> None:
    (tmp_path / "b.pdf").touch()
    (tmp_path / "a.pdf").touch()

    assert [path.name for path in find_pdfs(tmp_path)] == ["a.pdf", "b.pdf"]


def test_ignores_non_pdf_files(tmp_path: Path) -> None:
    (tmp_path / "report.pdf").touch()
    (tmp_path / "notes.txt").touch()

    assert [path.name for path in find_pdfs(tmp_path)] == ["report.pdf"]


def test_is_case_insensitive_about_the_extension(tmp_path: Path) -> None:
    (tmp_path / "report.PDF").touch()

    assert [path.name for path in find_pdfs(tmp_path)] == ["report.PDF"]


def test_an_empty_directory_returns_no_pdfs(tmp_path: Path) -> None:
    assert find_pdfs(tmp_path) == []


def test_is_not_recursive(tmp_path: Path) -> None:
    (tmp_path / "subfolder").mkdir()
    (tmp_path / "subfolder" / "nested.pdf").touch()

    assert find_pdfs(tmp_path) == []


def test_ignores_directories_named_like_a_pdf(tmp_path: Path) -> None:
    (tmp_path / "looks_like_a.pdf").mkdir()

    assert find_pdfs(tmp_path) == []


# --- sanitize_for_terminal ---


def test_leaves_a_normal_filename_unchanged() -> None:
    assert sanitize_for_terminal("report.pdf") == "report.pdf"


def test_escapes_rich_markup_syntax() -> None:
    assert sanitize_for_terminal("[bold]report[/bold].pdf") == r"\[bold]report\[/bold].pdf"


def test_strips_non_printable_control_characters() -> None:
    malicious = "report\x1b[31m.pdf"

    assert sanitize_for_terminal(malicious) == "report[31m.pdf"


def test_keeps_accented_and_non_latin_printable_characters() -> None:
    assert sanitize_for_terminal("informe_día_café.pdf") == "informe_día_café.pdf"


# --- resolve_choice ---


def test_a_valid_number_picks_that_pdf_from_the_list(tmp_path: Path) -> None:
    pdfs = [tmp_path / "a.pdf", tmp_path / "b.pdf"]

    assert resolve_choice("2", pdfs) == pdfs[1]


def test_leading_and_trailing_whitespace_is_ignored(tmp_path: Path) -> None:
    pdfs = [tmp_path / "a.pdf"]

    assert resolve_choice("  1  ", pdfs) == pdfs[0]


def test_an_out_of_range_number_is_treated_as_a_literal_path() -> None:
    assert resolve_choice("99", []) == Path("99")


def test_zero_is_treated_as_a_literal_path_not_the_first_item(tmp_path: Path) -> None:
    pdfs = [tmp_path / "a.pdf"]

    assert resolve_choice("0", pdfs) == Path("0")


def test_typed_text_is_returned_as_a_path() -> None:
    assert resolve_choice("C:/Users/me/report.pdf", []) == Path("C:/Users/me/report.pdf")


# --- run_menu ---


@pytest.fixture
def mock_convert(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    monkeypatch.setattr(menu_module, "convert_pdf_to_md", mock)
    return mock


def _answer_prompts(monkeypatch: pytest.MonkeyPatch, *answers: str) -> None:
    monkeypatch.setattr(menu_module.Prompt, "ask", MagicMock(side_effect=list(answers)))


def _answer_confirms(monkeypatch: pytest.MonkeyPatch, *answers: bool) -> None:
    monkeypatch.setattr(menu_module.Confirm, "ask", MagicMock(side_effect=list(answers)))


def test_choosing_a_number_converts_that_pdf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_convert: MagicMock
) -> None:
    (tmp_path / "a.pdf").touch()
    (tmp_path / "b.pdf").touch()
    monkeypatch.chdir(tmp_path)
    mock_convert.return_value = tmp_path / "b.md"
    _answer_prompts(monkeypatch, "2")
    _answer_confirms(monkeypatch, False)

    exit_code = run_menu([])

    assert exit_code == EXIT_SUCCESS
    assert mock_convert.call_args.args[0] == tmp_path / "b.pdf"


def test_no_pdfs_found_asks_for_a_typed_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_convert: MagicMock
) -> None:
    monkeypatch.chdir(tmp_path)
    typed_path = str(tmp_path / "typed.pdf")
    mock_convert.return_value = tmp_path / "typed.md"
    _answer_prompts(monkeypatch, typed_path)
    _answer_confirms(monkeypatch, False)

    run_menu([])

    assert mock_convert.call_args.args[0] == Path(typed_path)


def test_a_wrong_password_is_retried_until_correct(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_convert: MagicMock
) -> None:
    pdf = tmp_path / "secret.pdf"
    pdf.touch()
    monkeypatch.chdir(tmp_path)
    mock_convert.side_effect = [InvalidPasswordError(pdf), tmp_path / "secret.md"]
    _answer_prompts(monkeypatch, "1", "hunter2")
    _answer_confirms(monkeypatch, False)

    exit_code = run_menu([])

    assert exit_code == EXIT_SUCCESS
    assert mock_convert.call_count == 2
    assert mock_convert.call_args.kwargs["password"] == "hunter2"


def test_a_conversion_error_is_reported_like_the_cli_and_stops_the_loop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_convert: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pdf = tmp_path / "bad.pdf"
    pdf.touch()
    monkeypatch.chdir(tmp_path)
    mock_convert.side_effect = CorruptFileError(pdf)
    _answer_prompts(monkeypatch, "1")
    _answer_confirms(monkeypatch, False)

    exit_code = run_menu([])

    assert exit_code == EXIT_CORRUPT_FILE
    assert "corrupted" in capsys.readouterr().err


def test_answering_yes_converts_another_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_convert: MagicMock
) -> None:
    (tmp_path / "a.pdf").touch()
    monkeypatch.chdir(tmp_path)
    mock_convert.return_value = tmp_path / "a.md"
    _answer_prompts(monkeypatch, "1", "1")
    _answer_confirms(monkeypatch, True, False)

    run_menu([])

    assert mock_convert.call_count == 2


def test_keyboard_interrupt_exits_cleanly_without_a_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_convert: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(menu_module.Prompt, "ask", MagicMock(side_effect=KeyboardInterrupt))

    exit_code = run_menu([])

    assert exit_code == EXIT_SUCCESS
    assert "Traceback" not in capsys.readouterr().err
    mock_convert.assert_not_called()


def test_progress_messages_are_printed_while_converting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_convert: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "a.pdf").touch()
    monkeypatch.chdir(tmp_path)
    _answer_prompts(monkeypatch, "1")
    _answer_confirms(monkeypatch, False)

    def _fake_convert(input_path: Path, password: str | None = None, on_progress=None) -> Path:
        on_progress(menu_module.ConversionStage.STARTED)
        return tmp_path / "a.md"

    mock_convert.side_effect = _fake_convert

    run_menu([])

    assert "Starting conversion" in capsys.readouterr().out


def test_an_unexpected_error_shows_a_generic_message_without_a_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_convert: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "a.pdf").touch()
    monkeypatch.chdir(tmp_path)
    mock_convert.side_effect = RuntimeError("bug!")
    _answer_prompts(monkeypatch, "1")
    _answer_confirms(monkeypatch, False)

    exit_code = run_menu([])

    error_output = capsys.readouterr().err
    assert exit_code == menu_module.EXIT_UNEXPECTED_ERROR
    assert "unexpected error" in error_output.lower()
    assert "Traceback" not in error_output


def test_lang_flag_changes_the_interface_language(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_convert: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    mock_convert.return_value = tmp_path / "x.md"
    _answer_prompts(monkeypatch, str(tmp_path / "x.pdf"))
    _answer_confirms(monkeypatch, False)

    run_menu(["--lang", "es"])

    assert "Convierte un PDF a Markdown" in capsys.readouterr().out


def test_a_malicious_filename_is_sanitized_before_being_listed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_convert: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "[bold]evil.pdf").touch()
    monkeypatch.chdir(tmp_path)
    mock_convert.return_value = tmp_path / "out.md"
    _answer_prompts(monkeypatch, "1")
    _answer_confirms(monkeypatch, False)

    run_menu([])

    # rich's markup parser consumes the escaping backslash on render: seeing the
    # literal brackets survive here proves "[bold]" was NOT interpreted as a style
    # tag (which would have silently swallowed it, leaving just "evil.pdf").
    assert "[bold]evil.pdf" in capsys.readouterr().out
