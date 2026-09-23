import os
import shutil
import warnings
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.document import ErrorItem, FailureCategory
from docling.datamodel.pipeline_options import EasyOcrOptions
from docling_core.types.doc.document import DoclingDocument

from markwright.core.converter import ConversionStage, ConversionWarning, convert_pdf_to_md
from markwright.core.exceptions import (
    CorruptFileError,
    InvalidPasswordError,
    OutputWriteError,
    UnsupportedFileError,
)

# --- Success cases ---


def test_pdf_without_pictures_produces_markdown_without_images_folder(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    mock_docling_convert: MagicMock,
) -> None:
    input_path = plain_pdf_factory()
    mock_docling_convert.return_value = conversion_result_factory(text="Hello world")

    result_path = convert_pdf_to_md(input_path)

    assert result_path == input_path.with_suffix(".md")
    assert "Hello world" in result_path.read_text(encoding="utf-8")
    assert not (input_path.parent / "input_images").exists()


def test_pdf_with_pictures_produces_markdown_and_referenced_images_folder(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    mock_docling_convert: MagicMock,
) -> None:
    input_path = plain_pdf_factory()
    mock_docling_convert.return_value = conversion_result_factory(
        text="Hello world", with_picture=True
    )

    result_path = convert_pdf_to_md(input_path)

    images_dir = input_path.parent / "input_images"
    assert images_dir.is_dir()
    assert any(images_dir.iterdir())
    markdown = result_path.read_text(encoding="utf-8")
    assert "input_images/" in markdown


def test_headings_and_lists_are_preserved_as_markdown_syntax(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    mock_docling_convert: MagicMock,
) -> None:
    input_path = plain_pdf_factory()
    mock_docling_convert.return_value = conversion_result_factory(
        heading="My Heading", text="Body text", list_items=["item one", "item two"]
    )

    result_path = convert_pdf_to_md(input_path)

    markdown = result_path.read_text(encoding="utf-8")
    assert "## My Heading" in markdown
    assert "- item one" in markdown
    assert "- item two" in markdown


def test_on_progress_is_called_for_each_stage_in_order(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    mock_docling_convert: MagicMock,
) -> None:
    input_path = plain_pdf_factory()
    mock_docling_convert.return_value = conversion_result_factory()
    seen_stages: list[ConversionStage] = []

    convert_pdf_to_md(input_path, on_progress=lambda stage, warning=None: seen_stages.append(stage))

    assert seen_stages == [
        ConversionStage.STARTED,
        ConversionStage.CONVERTING,
        ConversionStage.WRITING,
        ConversionStage.DONE,
    ]


def test_on_progress_none_does_not_raise(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    mock_docling_convert: MagicMock,
) -> None:
    input_path = plain_pdf_factory()
    mock_docling_convert.return_value = conversion_result_factory()

    result_path = convert_pdf_to_md(input_path, on_progress=None)

    assert result_path.exists()


def test_encrypted_pdf_with_correct_password_converts_successfully(
    encrypted_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    mock_docling_convert: MagicMock,
) -> None:
    input_path = encrypted_pdf_factory(password="right-pw")
    mock_docling_convert.return_value = conversion_result_factory(text="Unlocked content")

    result_path = convert_pdf_to_md(input_path, password="right-pw")

    assert "Unlocked content" in result_path.read_text(encoding="utf-8")


def test_explicit_output_path_is_respected(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    mock_docling_convert: MagicMock,
    tmp_path: Path,
) -> None:
    input_path = plain_pdf_factory()
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    output_path = output_dir / "custom.md"
    mock_docling_convert.return_value = conversion_result_factory()

    result_path = convert_pdf_to_md(input_path, output_path=output_path)

    assert result_path == output_path


def test_returns_the_generated_markdown_path(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    mock_docling_convert: MagicMock,
) -> None:
    input_path = plain_pdf_factory()
    mock_docling_convert.return_value = conversion_result_factory()

    result_path = convert_pdf_to_md(input_path)

    assert isinstance(result_path, Path)
    assert result_path.is_file()


def test_uppercase_pdf_extension_is_accepted(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    mock_docling_convert: MagicMock,
) -> None:
    input_path = plain_pdf_factory(name="Report.PDF")
    mock_docling_convert.return_value = conversion_result_factory()

    result_path = convert_pdf_to_md(input_path)

    assert result_path == input_path.with_suffix(".md")


def test_relative_input_path_works_end_to_end(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    mock_docling_convert: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    plain_pdf_factory()
    monkeypatch.chdir(tmp_path)
    mock_docling_convert.return_value = conversion_result_factory()

    result_path = convert_pdf_to_md(Path("input.pdf"))

    assert result_path == tmp_path / "input.md"


def test_string_paths_are_accepted(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    mock_docling_convert: MagicMock,
    tmp_path: Path,
) -> None:
    input_path = plain_pdf_factory()
    mock_docling_convert.return_value = conversion_result_factory()

    result_path = convert_pdf_to_md(str(input_path), output_path=str(tmp_path / "out.md"))

    assert result_path == tmp_path / "out.md"


def test_minimal_empty_document_does_not_fail(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    mock_docling_convert: MagicMock,
) -> None:
    input_path = plain_pdf_factory()
    mock_docling_convert.return_value = conversion_result_factory(text=None)

    result_path = convert_pdf_to_md(input_path)

    assert result_path.exists()


def test_output_collision_uses_the_next_free_suffix(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    mock_docling_convert: MagicMock,
) -> None:
    input_path = plain_pdf_factory()
    (input_path.parent / "input.md").touch()
    mock_docling_convert.return_value = conversion_result_factory()

    result_path = convert_pdf_to_md(input_path)

    assert result_path == input_path.parent / "input_1.md"


_OFFLINE_VARIABLES = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")


def _run_and_capture_pipeline_options(
    monkeypatch: pytest.MonkeyPatch,
    input_path: Path,
    result: SimpleNamespace,
    environment: dict[str, str] | None = None,
) -> object:
    """Convert with a fake DocumentConverter class and return the pipeline options used.

    ``environment`` replaces ``os.environ`` for the run, so the offline flags the
    converter sets never leak into other tests.
    """
    fake_converter_class = MagicMock()
    fake_converter_class.return_value.convert.return_value = result
    monkeypatch.setattr("docling.document_converter.DocumentConverter", fake_converter_class)
    if environment is not None:
        monkeypatch.setattr(os, "environ", environment)

    convert_pdf_to_md(input_path)

    format_options = fake_converter_class.call_args.kwargs["format_options"]
    return format_options[InputFormat.PDF].pipeline_options


def _environment_without_offline_flags() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in _OFFLINE_VARIABLES}


def test_pipeline_uses_easyocr_and_generates_picture_images(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    options = _run_and_capture_pipeline_options(
        monkeypatch, plain_pdf_factory(), conversion_result_factory()
    )

    assert isinstance(options.ocr_options, EasyOcrOptions)
    assert options.generate_picture_images is True


def test_a_local_models_folder_is_used_and_keeps_the_conversion_offline(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    models = tmp_path / "models"
    monkeypatch.setattr("markwright.core.converter.find_models_dir", lambda: models)
    environment = _environment_without_offline_flags()

    options = _run_and_capture_pipeline_options(
        monkeypatch, plain_pdf_factory(), conversion_result_factory(), environment
    )

    assert options.artifacts_path == models
    assert environment["HF_HUB_OFFLINE"] == "1"
    assert environment["TRANSFORMERS_OFFLINE"] == "1"


def test_an_explicit_offline_setting_from_the_user_is_respected(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("markwright.core.converter.find_models_dir", lambda: tmp_path)
    environment = _environment_without_offline_flags() | {"HF_HUB_OFFLINE": "0"}

    _run_and_capture_pipeline_options(
        monkeypatch, plain_pdf_factory(), conversion_result_factory(), environment
    )

    assert environment["HF_HUB_OFFLINE"] == "0"


def test_third_party_chatter_is_silenced_for_end_users(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _environment_without_offline_flags()
    environment.pop("TQDM_DISABLE", None)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _run_and_capture_pipeline_options(
            monkeypatch, plain_pdf_factory(), conversion_result_factory(), environment
        )
        warnings.warn_explicit(
            "deprecated", UserWarning, "torch/ao/rnn.py", 1, module="torch.ao.nn.quantized"
        )

    assert environment["TQDM_DISABLE"] == "1"
    assert caught == []


def test_the_runtime_is_prepared_before_any_docling_import(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Decrypting a protected PDF imports docling too, so the setup must come first."""
    environment = _environment_without_offline_flags()
    environment.pop("TQDM_DISABLE", None)
    seen: dict[str, str | None] = {}

    def spy(input_path: Path, password: str | None = None) -> Path:
        seen["tqdm"] = environment.get("TQDM_DISABLE")
        return input_path

    monkeypatch.setattr("markwright.core.converter.prepare_docling_source", spy)

    _run_and_capture_pipeline_options(
        monkeypatch, plain_pdf_factory(), conversion_result_factory(), environment
    )

    assert seen["tqdm"] == "1"


def test_without_a_local_models_folder_the_docling_defaults_are_left_untouched(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _environment_without_offline_flags()

    options = _run_and_capture_pipeline_options(
        monkeypatch, plain_pdf_factory(), conversion_result_factory(), environment
    )

    assert options.artifacts_path is None
    assert not set(_OFFLINE_VARIABLES) & environment.keys()


# --- Partial success ---


def test_partial_success_with_transient_categories_is_marked_retryable(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    error_item_factory: Callable[..., ErrorItem],
    mock_docling_convert: MagicMock,
) -> None:
    input_path = plain_pdf_factory()
    mock_docling_convert.return_value = conversion_result_factory(
        status=ConversionStatus.PARTIAL_SUCCESS,
        errors=[error_item_factory(FailureCategory.TIMEOUT, page_no=3)],
    )
    seen: list[tuple[ConversionStage, ConversionWarning | None]] = []

    result_path = convert_pdf_to_md(
        input_path, on_progress=lambda stage, warning=None: seen.append((stage, warning))
    )

    assert result_path.exists()
    warnings = [w for stage, w in seen if stage == ConversionStage.PARTIAL_SUCCESS]
    assert len(warnings) == 1
    assert warnings[0].retryable is True
    assert warnings[0].categories == ("timeout",)
    assert warnings[0].affected_pages == (3,)


def test_partial_success_with_content_related_category_is_not_marked_retryable(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    error_item_factory: Callable[..., ErrorItem],
    mock_docling_convert: MagicMock,
) -> None:
    input_path = plain_pdf_factory()
    mock_docling_convert.return_value = conversion_result_factory(
        status=ConversionStatus.PARTIAL_SUCCESS,
        errors=[
            error_item_factory(FailureCategory.BACKEND_FAILURE, page_no=1),
            error_item_factory(FailureCategory.TIMEOUT, page_no=2),
        ],
    )
    seen: list[tuple[ConversionStage, ConversionWarning | None]] = []

    result_path = convert_pdf_to_md(
        input_path, on_progress=lambda stage, warning=None: seen.append((stage, warning))
    )

    assert result_path.exists()
    warnings = [w for stage, w in seen if stage == ConversionStage.PARTIAL_SUCCESS]
    assert warnings[0].retryable is False


# --- Error cases ---


def test_missing_input_file_raises_unsupported_file_error(tmp_path: Path) -> None:
    with pytest.raises(UnsupportedFileError):
        convert_pdf_to_md(tmp_path / "does_not_exist.pdf")


def test_input_path_that_is_a_directory_raises_unsupported_file_error(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "a_folder.pdf"
    directory.mkdir()

    with pytest.raises(UnsupportedFileError):
        convert_pdf_to_md(directory)


def test_non_pdf_extension_raises_unsupported_file_error(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("not a pdf")

    with pytest.raises(UnsupportedFileError):
        convert_pdf_to_md(path)


def test_encrypted_pdf_without_password_raises_invalid_password_error(
    encrypted_pdf_factory: Callable[..., Path],
) -> None:
    input_path = encrypted_pdf_factory(password="right-pw")

    with pytest.raises(InvalidPasswordError):
        convert_pdf_to_md(input_path)


def test_docling_failure_raises_corrupt_file_error(
    plain_pdf_factory: Callable[..., Path], mock_docling_convert: MagicMock
) -> None:
    input_path = plain_pdf_factory()
    mock_docling_convert.side_effect = RuntimeError("docling exploded")

    with pytest.raises(CorruptFileError):
        convert_pdf_to_md(input_path)


def test_corrupt_pdf_content_detected_before_docling_raises_corrupt_file_error(
    tmp_path: Path, mock_docling_convert: MagicMock
) -> None:
    input_path = tmp_path / "garbage.pdf"
    input_path.write_bytes(b"this is not a real pdf file at all")

    with pytest.raises(CorruptFileError):
        convert_pdf_to_md(input_path)

    mock_docling_convert.assert_not_called()


def test_write_failure_raises_output_write_error_and_cleans_up(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    mock_docling_convert: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_path = plain_pdf_factory()
    mock_docling_convert.return_value = conversion_result_factory(with_picture=True)
    monkeypatch.setattr(
        DoclingDocument,
        "save_as_markdown",
        MagicMock(side_effect=OSError("disk full")),
    )

    with pytest.raises(OutputWriteError):
        convert_pdf_to_md(input_path)

    assert not (input_path.parent / "input.md").exists()
    assert not (input_path.parent / "input_images").exists()


def test_invalid_destination_directory_fails_before_calling_docling(
    plain_pdf_factory: Callable[..., Path],
    mock_docling_convert: MagicMock,
    tmp_path: Path,
) -> None:
    input_path = plain_pdf_factory()
    missing_dir_output = tmp_path / "does_not_exist" / "final.md"

    with pytest.raises(OutputWriteError):
        convert_pdf_to_md(input_path, output_path=missing_dir_output)

    mock_docling_convert.assert_not_called()


def test_output_write_error_is_raised_even_if_cleanup_itself_fails(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    mock_docling_convert: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_path = plain_pdf_factory()
    mock_docling_convert.return_value = conversion_result_factory()
    original_cause = OSError("disk full")
    monkeypatch.setattr(
        DoclingDocument, "save_as_markdown", MagicMock(side_effect=original_cause)
    )
    monkeypatch.setattr(Path, "unlink", MagicMock(side_effect=OSError("cleanup failed")))
    monkeypatch.setattr(shutil, "rmtree", MagicMock(side_effect=OSError("cleanup failed")))

    with pytest.raises(OutputWriteError) as exc_info:
        convert_pdf_to_md(input_path)

    assert exc_info.value.__cause__ is original_cause


def test_on_progress_exception_propagates_unwrapped(
    plain_pdf_factory: Callable[..., Path],
    conversion_result_factory: Callable[..., SimpleNamespace],
    mock_docling_convert: MagicMock,
) -> None:
    input_path = plain_pdf_factory()
    mock_docling_convert.return_value = conversion_result_factory()

    def broken_callback(stage: ConversionStage, warning: ConversionWarning | None = None) -> None:
        raise RuntimeError("adapter bug")

    with pytest.raises(RuntimeError, match="adapter bug"):
        convert_pdf_to_md(input_path, on_progress=broken_callback)
