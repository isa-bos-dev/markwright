from __future__ import annotations

import re
from typing import TYPE_CHECKING

from docling_core.types.doc import DocItemLabel

from markwright.core.document_tree import move_item_after

if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument
    from docling_core.types.doc.items.text import TextItem

# A paragraph starting with "(1) ", "(23) ", etc. — the shape docling extracts
# a right-margin footnote as (confirmed empirically: it keeps the author's own
# "(N)" numbering, but loses its position relative to what it explains).
_FOOTNOTE_START = re.compile(r"^\((\d{1,3})\)\s")


def relocate_footnotes(document: DoclingDocument) -> None:
    """Move a footnote-shaped paragraph to sit right after what it explains.

    Some PDFs lay a footnote out as a right-margin note rather than at the
    bottom of the page; docling extracts it as an ordinary paragraph, and the
    margin column's reading order often places that paragraph well after the
    text it explains (FID-FR-003). This pairs each "(N) ..." paragraph with
    its inline marker and relocates the paragraph to immediately follow it.

    The marker itself is often glued straight onto the preceding word with no
    space (PDF extraction drops the superscript's visual gap), so a lone digit
    is too weak a signal on its own — "10" shows up in page numbers, dates,
    units. The real safeguard is sequential order: footnote markers are
    numbered 1, 2, 3... and appear in that order through the document, so
    once marker N is found, marker N+1 is only looked for *after* it. A
    footnote whose marker can't be found in order is left exactly where
    docling put it, rather than guessed at.
    """
    candidates = [item for item in document.texts if item.label == DocItemLabel.TEXT]
    footnotes = [
        (item, match.group(1))
        for item in candidates
        if (match := _FOOTNOTE_START.match(item.text)) is not None
    ]
    # A footnote paragraph itself is never a valid anchor for another one
    # (e.g. a citation's own "vol. 31" shouldn't be mistaken for a marker).
    anchor_pool = [item for item in candidates if _FOOTNOTE_START.match(item.text) is None]

    search_start = 0
    for footnote, number in footnotes:
        found = _find_anchor(anchor_pool, number, search_start)
        if found is None:
            continue
        anchor, index = found
        _mark_superscript(anchor, number)
        move_item_after(document, item=footnote, anchor=anchor)
        search_start = index + 1


def _find_anchor(
    anchor_pool: list[TextItem], number: str, search_start: int
) -> tuple[TextItem, int] | None:
    pattern = _marker_pattern(number)
    for index in range(search_start, len(anchor_pool)):
        item = anchor_pool[index]
        match = pattern.search(item.text)
        # A marker never opens its own paragraph — that shape belongs to a
        # numbered list item or heading ("1. Primer punto"), not a reference
        # sitting mid-sentence.
        if match is not None and match.start() > 0:
            return item, index
    return None


def _marker_pattern(number: str) -> re.Pattern[str]:
    # An isolated digit token: optionally glued to the previous word (PDF
    # extraction usually drops the space a superscript had), bounded by
    # non-digits on both sides so "1" doesn't match inside "10" or "2014".
    # It may NOT be glued — directly, or via a hyphen — to a following word
    # ("3D", "10mg", "3-tuplas" are units/compound terms), nor come right
    # after a literal "^" (plain-text exponent notation, "10^3"). All three
    # found against the real sample PDF, wrongly matched as markers before
    # these guards.
    return re.compile(rf"(?<!\^)[ \t]?(?<!\d){re.escape(number)}(?!-?[\wÀ-ÿ])")


def _mark_superscript(item: TextItem, number: str) -> None:
    item.text = _marker_pattern(number).sub(f"<sup>{number}</sup>", item.text, count=1)
