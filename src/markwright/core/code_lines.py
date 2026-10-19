from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING

from docling_core.types.doc import CodeItem

if TYPE_CHECKING:
    from docling_core.types.doc import BoundingBox
    from docling_core.types.doc.document import DoclingDocument

# Returns the PDF's own text-layer text inside ``bbox`` on page ``page_no``
# (1-based, BOTTOMLEFT origin as in docling's provenance), line breaks kept.
type RegionReader = Callable[[int, BoundingBox], str]

# pdfium marks a line-end hyphenation point with U+FFFE; not real content.
_NOT_CONTENT = re.compile(r"[\s￾]")


def restore_code_line_breaks(document: DoclingDocument, read_region: RegionReader) -> None:
    """Give a code block back the line breaks docling flattened into spaces.

    docling joins every text cell of a code region with a single space, so a
    multi-line listing reaches the Markdown as one endless line. The PDF's own
    text layer still has the lines: this re-reads the block's region from it
    and uses that instead — but only when, ignoring whitespace, it is exactly
    the text docling extracted. That check makes the swap provably lossless:
    a block OCR'd from a screenshot has no text layer (empty read), and a
    region that catches a neighbouring line reads differently; both are left
    exactly as docling produced them.
    """
    for item in document.texts:
        if not isinstance(item, CodeItem) or not item.prov:
            continue
        provenance = item.prov[0]
        raw = read_region(provenance.page_no, provenance.bbox)
        if not raw or _squash(raw) != _squash(item.text):
            continue
        lines = raw.replace("\r\n", "\n").replace("\r", "\n").replace("￾", "").split("\n")
        item.text = "\n".join(line.rstrip() for line in lines).strip("\n")


def _squash(text: str) -> str:
    return _NOT_CONTENT.sub("", text)
