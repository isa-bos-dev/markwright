from __future__ import annotations

import re
from typing import TYPE_CHECKING

from docling_core.types.doc import ListGroup, ListItem

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


# A list number as the PDF printed it: "3.", "1.1.", "2)" or "12.1".
_NUMBER = re.compile(r"\d+(?:\.\d+)*[.)]?")
# The same number left glued to the text when docling missed it as a marker
# ("3.Disassemblers"); a letter must follow, so "3.5 GHz" is not taken for one.
_GLUED_NUMBER = re.compile(r"^(\d+(?:\.\d+)*\.)\s*(?=[^\W\d_])")


def keep_original_list_numbers(document: DoclingDocument) -> None:
    """Keep a list's printed numbers when renumbering it 1, 2, 3 would lie.

    The Markdown is written with docling's original-marker mode off, so every
    enumerated list is renumbered from 1 by position (which is what turns a
    "1)" list into a clean "1."). For a list whose own numbers don't follow
    that sequence — a table of contents ("1.", "1.1.", "1.2.", "2."...) is
    the typical case — the renumbering replaced the real section numbers with
    wrong ones ("1.1. Reverse Engineering" came out as "2."). Such a list keeps
    each number as the start of its item's text instead, as a bullet list.

    Only a list where *every* item carries a number is touched: anything else
    is not reliably a numbered list, and is left to the default rendering.
    """
    for group in document.groups:
        if not isinstance(group, ListGroup) or not group.children:
            continue
        entries = [_printed_number(child.resolve(document)) for child in group.children]
        numbered = [entry for entry in entries if entry is not None]
        if len(numbered) < len(entries):
            continue
        if all(
            number.rstrip(".)") == str(position)
            for position, (_, number, _) in enumerate(numbered, 1)
        ):
            continue
        for item, number, text in numbered:
            item.text = f"{number} {text}"
            item.marker = ""
            item.enumerated = False


def _printed_number(node: object) -> tuple[ListItem, str, str] | None:
    """The item with its printed number and the text after it, if it has one."""
    if not isinstance(node, ListItem):
        return None
    if _NUMBER.fullmatch(node.marker):
        return node, node.marker, node.text
    if not node.marker and (match := _GLUED_NUMBER.match(node.text)):
        return node, match.group(1), node.text[match.end() :]
    return None
