from pathlib import Path

import pytest

from markwright.core.exceptions import OutputWriteError
from markwright.core.paths import resolve_output_paths

# --- Success cases ---


def test_no_output_path_and_no_collision_uses_input_dir_and_basename(tmp_path: Path) -> None:
    input_path = tmp_path / "report.pdf"
    input_path.touch()

    result = resolve_output_paths(input_path)

    assert result.markdown_path == tmp_path / "report.md"
    assert result.images_dir == tmp_path / "report_images"


def test_explicit_output_path_with_correct_extension_is_used_as_is(tmp_path: Path) -> None:
    input_path = tmp_path / "report.pdf"
    input_path.touch()
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    output_path = output_dir / "final.md"

    result = resolve_output_paths(input_path, output_path)

    assert result.markdown_path == output_path
    assert result.images_dir == output_dir / "final_images"


def test_relative_output_path_is_resolved_to_absolute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "report.pdf"
    input_path.touch()

    result = resolve_output_paths(input_path, Path("final.md"))

    assert result.markdown_path == tmp_path / "final.md"
    assert result.markdown_path.is_absolute()


def test_output_path_without_extension_gets_md_appended(tmp_path: Path) -> None:
    input_path = tmp_path / "report.pdf"
    input_path.touch()

    result = resolve_output_paths(input_path, tmp_path / "final")

    assert result.markdown_path == tmp_path / "final.md"


def test_output_path_with_different_extension_is_replaced_with_md(tmp_path: Path) -> None:
    input_path = tmp_path / "report.pdf"
    input_path.touch()

    result = resolve_output_paths(input_path, tmp_path / "notes.txt")

    assert result.markdown_path == tmp_path / "notes.md"


def test_collision_only_on_markdown_file_bumps_suffix_on_both(tmp_path: Path) -> None:
    input_path = tmp_path / "report.pdf"
    input_path.touch()
    (tmp_path / "report.md").touch()

    result = resolve_output_paths(input_path)

    assert result.markdown_path == tmp_path / "report_1.md"
    assert result.images_dir == tmp_path / "report_1_images"


def test_collision_only_on_images_dir_bumps_suffix_on_both(tmp_path: Path) -> None:
    input_path = tmp_path / "report.pdf"
    input_path.touch()
    (tmp_path / "report_images").mkdir()

    result = resolve_output_paths(input_path)

    assert result.markdown_path == tmp_path / "report_1.md"
    assert result.images_dir == tmp_path / "report_1_images"


def test_multiple_collisions_use_first_free_suffix(tmp_path: Path) -> None:
    input_path = tmp_path / "report.pdf"
    input_path.touch()
    (tmp_path / "report.md").touch()
    (tmp_path / "report_1.md").touch()
    (tmp_path / "report_1_images").mkdir()

    result = resolve_output_paths(input_path)

    assert result.markdown_path == tmp_path / "report_2.md"
    assert result.images_dir == tmp_path / "report_2_images"


def test_filename_with_spaces_accents_and_parentheses(tmp_path: Path) -> None:
    input_path = tmp_path / "Informe Técnico (v2).pdf"
    input_path.touch()

    result = resolve_output_paths(input_path)

    assert result.markdown_path == tmp_path / "Informe Técnico (v2).md"
    assert result.images_dir == tmp_path / "Informe Técnico (v2)_images"


def test_relative_input_path_is_resolved_to_absolute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "report.pdf"
    input_path.touch()

    result = resolve_output_paths(Path("report.pdf"))

    assert result.markdown_path == tmp_path / "report.md"
    assert result.markdown_path.is_absolute()
    assert result.images_dir.is_absolute()


def test_function_is_pure_and_does_not_touch_the_filesystem(tmp_path: Path) -> None:
    input_path = tmp_path / "report.pdf"
    input_path.touch()
    before = set(tmp_path.iterdir())

    resolve_output_paths(input_path)

    after = set(tmp_path.iterdir())
    assert before == after


# --- Error cases ---


def test_output_path_pointing_to_existing_directory_raises(tmp_path: Path) -> None:
    input_path = tmp_path / "report.pdf"
    input_path.touch()
    existing_dir = tmp_path / "already_a_folder"
    existing_dir.mkdir()

    with pytest.raises(OutputWriteError):
        resolve_output_paths(input_path, existing_dir)


def test_missing_destination_directory_raises(tmp_path: Path) -> None:
    input_path = tmp_path / "report.pdf"
    input_path.touch()
    missing_dir_output = tmp_path / "does_not_exist" / "final.md"

    with pytest.raises(OutputWriteError):
        resolve_output_paths(input_path, missing_dir_output)


def test_collision_limit_exceeded_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import markwright.core.paths as paths_module

    monkeypatch.setattr(paths_module, "MAX_COLLISION_ATTEMPTS", 2)
    input_path = tmp_path / "report.pdf"
    input_path.touch()
    (tmp_path / "report.md").touch()
    (tmp_path / "report_1.md").touch()

    with pytest.raises(OutputWriteError):
        resolve_output_paths(input_path)
