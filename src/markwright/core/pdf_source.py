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

    import pypdfium2
    from docling.datamodel.base_models import DocumentStream
    from docling_core.types.doc import BoundingBox
    from PIL.Image import Image

    from markwright.core.code_lines import PdfRegions


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


# A region rendered as an image this many times its size in PDF points
# (2 = 144 dpi): sharp enough for a screenshot of code to stay legible.
_RENDER_SCALE = 2


@contextmanager
def open_pdf_regions(source: Path | DocumentStream) -> Iterator[PdfRegions]:
    """Read a region of the PDF itself: its text layer, or its rendered image."""
    import pypdfium2

    pdf = pypdfium2.PdfDocument(source if isinstance(source, Path) else source.stream.getvalue())
    try:
        yield _PdfiumRegions(pdf)
    finally:
        pdf.close()


class _PdfiumRegions:
    def __init__(self, pdf: pypdfium2.PdfDocument) -> None:
        self._pdf = pdf

    def text(self, page_no: int, bbox: BoundingBox) -> str:
        text_page = self._pdf[page_no - 1].get_textpage()
        # 1pt of slack: docling's bbox hugs the glyphs, so a strict bound can
        # clip the edge of the first or last character.
        return str(
            text_page.get_text_bounded(
                left=bbox.l - 1, bottom=bbox.b - 1, right=bbox.r + 1, top=bbox.t + 1
            )
        )

    def image(self, page_no: int, bbox: BoundingBox) -> Image:
        page = self._pdf[page_no - 1]
        width, height = page.get_size()
        left, bottom, right, top = _widen_to_embedded_image(page, bbox)
        # pdfium's crop is how much to cut off each edge (left, bottom, right,
        # top), not a box; 2pt of slack keeps the region's border visible.
        crop = (
            max(left - 2, 0),
            max(bottom - 2, 0),
            max(width - right - 2, 0),
            max(height - top - 2, 0),
        )
        image: Image = page.render(scale=_RENDER_SCALE, crop=crop).to_pil()
        return image


_PDFIUM_IMAGE_OBJECT = 3


def _widen_to_embedded_image(
    page: pypdfium2.PdfPage, bbox: BoundingBox
) -> tuple[float, float, float, float]:
    """The region, grown to cover any embedded image it mostly sits on.

    docling's box for text it OCR'd from a screenshot covers just that text,
    not the screenshot: rendering only the box cuts off whatever docling
    didn't read (the end of a long line, the editor's frame). An embedded
    image holding most of the box is that screenshot, so it is kept whole.
    """
    left, bottom, right, top = bbox.l, bbox.b, bbox.r, bbox.t
    area = max((right - left) * (top - bottom), 1.0)
    for obj in page.get_objects():
        if obj.type != _PDFIUM_IMAGE_OBJECT:
            continue
        img_left, img_bottom, img_right, img_top = obj.get_bounds()
        overlap_w = min(right, img_right) - max(left, img_left)
        overlap_h = min(top, img_top) - max(bottom, img_bottom)
        if overlap_w > 0 and overlap_h > 0 and overlap_w * overlap_h > area / 2:
            left, bottom = min(left, img_left), min(bottom, img_bottom)
            right, top = max(right, img_right), max(top, img_top)
    return left, bottom, right, top


def count_pages(source: Path | DocumentStream) -> int:
    """Page count of what ``prepare_docling_source`` returned, leaving a stream rewound."""
    if isinstance(source, Path):
        return len(PdfReader(source).pages)
    count = len(PdfReader(source.stream).pages)
    source.stream.seek(0)
    return count
