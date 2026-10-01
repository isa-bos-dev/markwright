from __future__ import annotations

from typing import TYPE_CHECKING

from docling_core.types.doc import DocItemLabel, Formatting

if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument


def italicize_captions(document: DoclingDocument) -> None:
    """Mark every image caption as italic (SYN-FR-004).

    docling never applies any style to a caption by default — this is new
    behavior Markwright adds, not a regression. Applies even when the
    caption also carries a hyperlink (the two compose: the link ends up
    wrapped in italics).
    """
    for item in document.texts:
        if item.label != DocItemLabel.CAPTION:
            continue
        if item.formatting is None:
            item.formatting = Formatting(italic=True)
        else:
            item.formatting.italic = True
