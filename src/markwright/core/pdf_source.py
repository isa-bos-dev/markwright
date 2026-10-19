from __future__ import annotations

from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from pypdf import PdfReader, PdfWriter
from pypdf.errors import WrongPasswordError

from markwright.core.exceptions import InvalidPasswordError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from docling.datamodel.base_models import DocumentStream
    from docling_core.types.doc import BoundingBox

    from markwright.core.code_lines import RegionReader


def prepare_docling_source(input_path: Path, password: str | None = None) -> Path | DocumentStream:
    """Return a source docling can convert directly.

    Unencrypted PDFs pass through untouched as a ``Path``. Encrypted PDFs are
    decrypted entirely in memory and returned as a ``DocumentStream`` — the
    decrypted content is never written to disk.
    """
    reader = PdfReader(input_path)
    if not reader.is_encrypted:
        return input_path

    if not password:
        raise InvalidPasswordError(input_path)

    try:
        reader = PdfReader(input_path, password=password)
    except WrongPasswordError:
        raise InvalidPasswordError(input_path) from None

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    buffer = BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    # Imported here: any docling import costs ~5 s (it loads PyTorch).
    from docling.datamodel.base_models import DocumentStream

    return DocumentStream(name=input_path.name, stream=buffer)


@contextmanager
def open_region_reader(source: Path | DocumentStream) -> Iterator[RegionReader]:
    """Read the PDF's own text layer inside a region, line breaks kept."""
    import pypdfium2

    pdf = pypdfium2.PdfDocument(source if isinstance(source, Path) else source.stream.getvalue())

    def read_region(page_no: int, bbox: BoundingBox) -> str:
        text_page = pdf[page_no - 1].get_textpage()
        # 1pt of slack: docling's bbox hugs the glyphs, so a strict bound can
        # clip the edge of the first or last character.
        return str(
            text_page.get_text_bounded(
                left=bbox.l - 1, bottom=bbox.b - 1, right=bbox.r + 1, top=bbox.t + 1
            )
        )

    try:
        yield read_region
    finally:
        pdf.close()


def count_pages(source: Path | DocumentStream) -> int:
    """Page count of what ``prepare_docling_source`` returned, leaving a stream rewound."""
    if isinstance(source, Path):
        return len(PdfReader(source).pages)
    count = len(PdfReader(source.stream).pages)
    source.stream.seek(0)
    return count
