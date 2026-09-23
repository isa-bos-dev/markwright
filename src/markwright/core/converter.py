import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from markwright.core.exceptions import (
    CorruptFileError,
    InvalidPasswordError,
    OutputWriteError,
    UnsupportedFileError,
)
from markwright.core.models import find_models_dir
from markwright.core.paths import OutputPaths, resolve_output_paths
from markwright.core.pdf_source import prepare_docling_source

# Categories considered likely environmental/transient (worth retrying).
# Anything else (content-specific failures, or unknown) is treated as not
# confidently retryable, to avoid promising a retry will help when it won't.
_TRANSIENT_FAILURE_CATEGORIES = frozenset(
    {"timeout", "capacity", "source_unavailable", "internal"}
)


class ConversionStage(StrEnum):
    STARTED = "started"
    CONVERTING = "converting"
    PARTIAL_SUCCESS = "partial_success"
    WRITING = "writing"
    DONE = "done"


@dataclass(frozen=True)
class ConversionWarning:
    """Details about a PARTIAL_SUCCESS conversion result."""

    retryable: bool
    categories: tuple[str, ...]
    affected_pages: tuple[int, ...]


OnProgress = Callable[[ConversionStage, ConversionWarning | None], None]


def convert_pdf_to_md(
    input_path: Path | str,
    output_path: Path | str | None = None,
    password: str | None = None,
    on_progress: OnProgress | None = None,
) -> Path:
    """Convert a local PDF file to Markdown, preserving structure and images.

    Returns the path to the generated Markdown file. Encrypted PDFs are
    decrypted in memory (see ``prepare_docling_source``). A PARTIAL_SUCCESS
    conversion still produces output; ``on_progress`` is called with details
    so the caller can decide whether to inform the user or offer a retry —
    this function never asks anything itself.
    """

    def report(stage: ConversionStage, warning: ConversionWarning | None = None) -> None:
        if on_progress is not None:
            on_progress(stage, warning)

    input_path = Path(input_path)
    if output_path is not None:
        output_path = Path(output_path)

    if not input_path.is_file():
        raise UnsupportedFileError(input_path)
    if input_path.suffix.lower() != ".pdf":
        raise UnsupportedFileError(input_path)

    report(ConversionStage.STARTED)

    output_paths = resolve_output_paths(input_path, output_path)

    try:
        source = prepare_docling_source(input_path, password)
    except InvalidPasswordError:
        raise
    except FileNotFoundError as exc:
        raise UnsupportedFileError(input_path) from exc
    except Exception as exc:
        raise CorruptFileError(input_path) from exc

    report(ConversionStage.CONVERTING)

    try:
        result = _build_converter().convert(source, raises_on_error=True)
    except Exception as exc:
        raise CorruptFileError(input_path) from exc

    if _is_partial_success(result):
        report(ConversionStage.PARTIAL_SUCCESS, _classify_partial_success(result))

    report(ConversionStage.WRITING)
    _write_markdown(result.document, output_paths)

    report(ConversionStage.DONE)
    return output_paths.markdown_path


def _build_converter():
    """Create the docling converter configured for Markwright.

    docling pulls in PyTorch, which takes ~5 s to import. Importing it here, on
    the first conversion, keeps the GUI window and ``--help`` instant.
    """
    models_dir = find_models_dir()
    if models_dir is not None:
        # Everything needed is on disk: never go online, so document content and
        # the user's IP address stay private. Must be set before docling is imported.
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pipeline_options = PdfPipelineOptions()
    pipeline_options.generate_picture_images = True
    # Force EasyOCR explicitly: docling's "auto" OCR mode may otherwise pick
    # RapidOCR, whose models are hosted on ModelScope rather than GitHub.
    pipeline_options.ocr_options = EasyOcrOptions()
    if models_dir is not None:
        pipeline_options.artifacts_path = models_dir
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )


def _is_partial_success(result) -> bool:
    from docling.datamodel.base_models import ConversionStatus

    return result.status == ConversionStatus.PARTIAL_SUCCESS


def _write_markdown(document, output_paths: OutputPaths) -> None:
    from docling_core.types.doc.base import ImageRefMode

    has_pictures = bool(document.pictures)
    try:
        if has_pictures:
            document.save_as_markdown(
                output_paths.markdown_path,
                artifacts_dir=Path(output_paths.images_dir.name),
                image_mode=ImageRefMode.REFERENCED,
            )
        else:
            document.save_as_markdown(output_paths.markdown_path)
    except OSError as exc:
        _cleanup_partial_output(output_paths)
        raise OutputWriteError(output_paths.markdown_path) from exc


def _cleanup_partial_output(output_paths: OutputPaths) -> None:
    try:
        if output_paths.markdown_path.exists():
            output_paths.markdown_path.unlink()
    except OSError:
        pass
    try:
        if output_paths.images_dir.exists():
            shutil.rmtree(output_paths.images_dir)
    except OSError:
        pass


def _classify_partial_success(result) -> ConversionWarning:
    categories = tuple(sorted({err.category.value for err in result.errors}))
    pages = tuple(
        sorted({err.page_no for err in result.errors if err.page_no is not None})
    )
    retryable = bool(categories) and all(c in _TRANSIENT_FAILURE_CATEGORIES for c in categories)
    return ConversionWarning(retryable=retryable, categories=categories, affected_pages=pages)
