from pathlib import Path

from markwright.cli.menu import find_pdfs, resolve_choice, sanitize_for_terminal

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
