from __future__ import annotations

import re
from typing import TYPE_CHECKING, Protocol

from docling_core.types.doc import CodeItem, ImageRef

from markwright.core.document_tree import move_item_after

if TYPE_CHECKING:
    from docling_core.types.doc import BoundingBox
    from docling_core.types.doc.document import DoclingDocument
    from PIL.Image import Image


class PdfRegions(Protocol):
    """A region of the PDF itself, by 1-based page and BOTTOMLEFT-origin box
    (as in docling's provenance)."""

    def text(self, page_no: int, bbox: BoundingBox) -> str:
        """The PDF's own text-layer text in the region, line breaks kept."""
        ...

    def image(self, page_no: int, bbox: BoundingBox) -> Image:
        """The region rendered as an image."""
        ...


# pdfium marks a line-end hyphenation point with U+FFFE; not real content.
_NOT_CONTENT = re.compile(r"[\s￾]")
# The resolution PdfRegions.image renders at (2x PDF points).
_IMAGE_DPI = 144


def restore_code_blocks(document: DoclingDocument, regions: PdfRegions) -> None:
    """Repair the two ways docling garbles a code block, using the PDF itself.

    docling joins every text cell of a code region with a single space, so a
    multi-line listing reaches the Markdown as one endless line. The PDF's
    text layer still has the lines: the block's region is re-read from it and
    used instead — but only when, ignoring whitespace, it is exactly the text
    docling extracted. That check makes the swap provably lossless.

    A block with (almost) no text layer at all was OCR'd from a screenshot of
    an editor or terminal: its text carries the editor's line numbers and OCR
    misreadings ("<stdio.h)", "buf[1e]"), which make a copy-pasted block worse
    than useless. Such a block is put back as the image it really is.

    A region whose text layer differs otherwise (e.g. it also caught a
    neighbouring line) is left exactly as docling produced it.
    """
    screenshots: list[CodeItem] = []
    for item in document.texts:
        if not isinstance(item, CodeItem) or not item.prov:
            continue
        provenance = item.prov[0]
        raw = regions.text(provenance.page_no, provenance.bbox)
        if raw and _squash(raw) == _squash(item.text):
            item.text = _clean_lines(raw)
        elif len(_squash(raw)) * 2 < len(_squash(item.text)):
            screenshots.append(item)

    for item in screenshots:
        _replace_with_image(document, item, regions)


def _replace_with_image(document: DoclingDocument, item: CodeItem, regions: PdfRegions) -> None:
    if item.parent is None:
        return
    provenance = item.prov[0]
    image = regions.image(provenance.page_no, provenance.bbox)
    picture = document.add_picture(
        image=ImageRef.from_pil(image, dpi=_IMAGE_DPI),
        prov=provenance,
        parent=item.parent.resolve(document),
    )
    move_item_after(document, item=picture, anchor=item)
    document.delete_items(node_items=[item])


def _clean_lines(raw: str) -> str:
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").replace("￾", "").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip("\n")


def _squash(text: str) -> str:
    return _NOT_CONTENT.sub("", text)
