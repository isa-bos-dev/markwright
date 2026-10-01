from __future__ import annotations

import re
from typing import TYPE_CHECKING

from docling_core.types.doc import DocItemLabel

if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument
    from docling_core.types.doc.items.text import TextItem

# A paragraph starting with "(1) ", "(23) ", etc. — the shape docling extracts
# a right-margin footnote as (confirmed empirically: it keeps the author's own
# "(N)" numbering, but loses its position relative to what it explains).
_FOOTNOTE_START = re.compile(r"^\((\d{1,3})\)\s")

# An isolated digit token (the superscript marker, flattened to plain text by
# PDF extraction) glued to neither neighbor: "... común 1 ." — word, space,
# digit, optional space, sentence punctuation.
_INLINE_MARKER = re.compile(r"(?<=\S)\s(\d{1,3})\s*([.,;:])")


def relocate_footnotes(document: DoclingDocument) -> None:
    """Move a footnote-shaped paragraph to sit right after what it explains.

    Some PDFs lay a footnote out as a right-margin note rather than at the
    bottom of the page; docling extracts it as an ordinary paragraph, and the
    margin column's reading order often places that paragraph well after the
    text it explains (FID-FR-003). This pairs a "(N) ..." paragraph with the
    paragraph on the same page containing an isolated "N" marker, rewrites
    that marker as ``<sup>N</sup>``, and relocates the footnote paragraph to
    immediately follow its match. A footnote with no matching marker on its
    page is left exactly where docling put it.
    """
    candidates = [item for item in document.texts if item.label == DocItemLabel.TEXT]
    footnote_matches = [
        (item, match)
        for item in candidates
        if (match := _FOOTNOTE_START.match(item.text)) is not None
    ]

    for footnote, match in footnote_matches:
        number = match.group(1)
        anchor = _find_anchor(candidates, footnote, number)
        if anchor is None:
            continue
        marker = re.compile(rf"(?<=\S)\s{re.escape(number)}\s*([.,;:])")
        anchor.text = marker.sub(rf"<sup>{number}</sup> \1", anchor.text, count=1)
        _move_after(document, item=footnote, anchor=anchor)


def _find_anchor(candidates: list[TextItem], footnote: TextItem, number: str) -> TextItem | None:
    pattern = re.compile(rf"(?<=\S)\s{re.escape(number)}\s*[.,;:]")
    for item in candidates:
        if item is footnote:
            continue
        if pattern.search(item.text) and _same_page_or_unconstrained(footnote, item):
            return item
    return None


def _same_page_or_unconstrained(a: TextItem, b: TextItem) -> bool:
    pages_a = {p.page_no for p in a.prov}
    pages_b = {p.page_no for p in b.prov}
    if not pages_a or not pages_b:
        return True
    return bool(pages_a & pages_b)


def _move_after(document: DoclingDocument, *, item: TextItem, anchor: TextItem) -> None:
    # .parent is always set for an item docling actually placed in the body
    # tree; the None case in its type is for a detached node, which a real
    # converted document never produces — skip rather than crash if it ever did.
    if item.parent is None or anchor.parent is None:
        return
    old_parent = item.parent.resolve(document)
    old_parent.children.remove(item.get_ref())
    new_parent = anchor.parent.resolve(document)
    index = new_parent.children.index(anchor.get_ref())
    new_parent.children.insert(index + 1, item.get_ref())
