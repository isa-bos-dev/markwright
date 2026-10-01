from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument

# U+FFFF is a Unicode noncharacter — it can never legitimately appear in real
# text, so finding it means a PDF font subset had no mapping for whatever
# glyph was there. Empirically (on a real sample PDF) it always replaced an
# inter-word space, never a letter — so a plain space is a safe substitute.
_MANGLED_SPACE = "￿"


def fix_mangled_spaces(document: DoclingDocument) -> None:
    """Replace a PDF font-encoding artifact (U+FFFF) with a normal space.

    Must run after fix_broken_list_markers (SYN-FR-001 vs. SYN-FR-003): that
    fix still needs to see the raw U+FFFF to recognize a marker docling
    failed to split out.
    """
    for item in document.texts:
        if _MANGLED_SPACE in item.text:
            item.text = item.text.replace(_MANGLED_SPACE, " ")
