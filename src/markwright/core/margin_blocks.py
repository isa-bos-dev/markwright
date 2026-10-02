from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from docling_core.types.doc import DocItemLabel

from markwright.core.document_tree import move_item_after
from markwright.core.footnotes import _FOOTNOTE_START

if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument
    from docling_core.types.doc.items.code import CodeItem
    from docling_core.types.doc.items.form import FieldHeadingItem, FieldValueItem
    from docling_core.types.doc.items.text import (
        FormulaItem,
        ListItem,
        SectionHeaderItem,
        TextItem,
        TitleItem,
    )

    # Matches DoclingDocument.texts' own declared element type.
    type DocTextItem = (
        TitleItem
        | SectionHeaderItem
        | ListItem
        | CodeItem
        | FormulaItem
        | FieldHeadingItem
        | FieldValueItem
        | TextItem
    )

# Not real body content, and not something that should ever anchor or be
# moved as part of a margin block.
_IGNORED_LABELS = frozenset(
    {DocItemLabel.PAGE_HEADER, DocItemLabel.PAGE_FOOTER, DocItemLabel.CAPTION}
)


def relocate_margin_blocks(document: DoclingDocument) -> None:
    """Move a whole right-margin section next to the paragraph it annotates.

    Some PDFs lay recommended-reading or example boxes out in a right-margin
    column rather than as footnotes — docling reads a page's main column
    fully, then the margin column fully, so a margin box's heading and
    paragraphs all end up dumped after everything else on the page, however
    far from the paragraph they actually annotate (MRG-FR-002). This is a
    broader case than FID-FR-003's numbered-citation footnotes: there's no
    "(N)" marker to search for, so detection is geometric instead of textual.

    The signal: within one page, body items normally read top-to-bottom —
    their ``bbox.t`` (BOTTOMLEFT origin) strictly decreases. When the main
    column ends and the margin column starts, ``t`` jumps back up instead of
    continuing to fall; that jump, not a hardcoded left-edge threshold (margin
    width varies by PDF), marks where the margin content begins. Each
    ``SECTION_HEADER`` inside that margin run starts its own sub-block (a
    page's margin column can hold several distinct boxes, read as one
    continuous run); each sub-block moves to follow whichever main-column
    item's own ``t`` is numerically closest to the sub-block's — validated
    against her hand-edited reference, where she placed each box right after
    the specific paragraph closest to it in height, not just the first one
    on the page.

    A footnote-shaped item ("(N) ...") inside a margin run is left for
    relocate_footnotes to handle on its own, by its own (more reliable,
    sequential-number) rule — never moved here. A sub-block consisting only
    of a footnote-shaped item is left exactly where docling put it.
    """
    by_page: dict[int, list[DocTextItem]] = defaultdict(list)
    for item in document.texts:
        if item.label in _IGNORED_LABELS or not item.prov:
            continue
        by_page[item.prov[0].page_no].append(item)

    for items in by_page.values():
        # A "jump back up" can only occur from the second item onward (the
        # first has nothing earlier to compare against), so whenever there's
        # a margin run at all, main_items already has at least one item.
        main_items, margin_items = _split_columns(items)
        if not margin_items:
            continue
        for raw_block in _group_into_blocks(margin_items):
            block = [item for item in raw_block if _FOOTNOTE_START.match(item.text) is None]
            if not block:
                continue
            anchor = _nearest_by_top(block[0], main_items)
            for item in reversed(block):
                move_item_after(document, item=item, anchor=anchor)


def _split_columns(items: list[DocTextItem]) -> tuple[list[DocTextItem], list[DocTextItem]]:
    """Split a page's items at the first "jump back up" in reading order."""
    last_t: float | None = None
    split_index = len(items)
    for index, item in enumerate(items):
        top = item.prov[0].bbox.t
        if last_t is not None and top > last_t:
            split_index = index
            break
        last_t = top
    return items[:split_index], items[split_index:]


def _group_into_blocks(items: list[DocTextItem]) -> list[list[DocTextItem]]:
    blocks: list[list[DocTextItem]] = []
    for item in items:
        if not blocks or item.label == DocItemLabel.SECTION_HEADER:
            blocks.append([])
        blocks[-1].append(item)
    return blocks


def _nearest_by_top(item: DocTextItem, candidates: list[DocTextItem]) -> DocTextItem:
    target = item.prov[0].bbox.t
    return min(candidates, key=lambda candidate: abs(candidate.prov[0].bbox.t - target))
