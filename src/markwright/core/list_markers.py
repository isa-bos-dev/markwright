from __future__ import annotations

import re
from typing import TYPE_CHECKING

from docling_core.types.doc import ListItem

if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument

# "1)" or "a)" at the very start, followed by the space docling expects to
# split marker from content — or by U+FFFF, when the PDF's own font encoding
# mangled that space (see text_sanitization.fix_mangled_spaces, which must
# run *after* this: once the space is normalized this pattern can't tell a
# broken marker from one that was never there).
_BROKEN_MARKER = re.compile(r"^(\d{1,3}\)|[a-z]\))[ \t￿]+")


def fix_broken_list_markers(document: DoclingDocument) -> None:
    """Reclassify a list item docling failed to recognize as enumerated.

    A "1) ..." or "a) ..." marker is only split from the item's text when
    docling's own parser recognizes it as a marker (setting ``enumerated``
    and ``marker``); when the space right after it is mangled (SYN-FR-001),
    that recognition fails and the raw marker stays glued to the item's own
    text instead. This repeats docling's own split by hand for exactly that
    case, so FID/SYN-FR-003's list-rendering fix can treat it as a normal
    enumerated item afterwards (SYN-FR-003).
    """
    for item in document.texts:
        if not isinstance(item, ListItem) or item.enumerated or item.marker:
            continue
        match = _BROKEN_MARKER.match(item.text)
        if match is None:
            continue
        item.marker = match.group(1)
        item.text = item.text[match.end() :]
        item.enumerated = True
