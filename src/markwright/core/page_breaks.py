from __future__ import annotations

from itertools import groupby
from typing import TYPE_CHECKING

from docling_core.types.doc import CodeItem, DocItem, DocItemLabel, ListItem, TextItem

from markwright.core.document_tree import is_inside_figure

if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument
    from docling_core.types.doc.items.node import NodeItem

# Repeated on every page, not part of the flow a page break interrupts.
_FURNITURE = frozenset({DocItemLabel.PAGE_HEADER, DocItemLabel.PAGE_FOOTER})
# A continuation starts within this much of the cut item's left edge: further
# right, it is a margin-column item, not the same column carrying on.
_SAME_COLUMN_POINTS = 25.0
# A list item's own text is indented past its bullet; a continuation that
# starts indented like that belongs to the bullet, even after a full stop.
_BULLET_INDENT_POINTS = 5.0
# How far right of the next page's first item the previous page's last item
# may start and still be the same column (beyond: a margin box, skipped).
_MARGIN_POINTS = 30.0


def join_across_page_breaks(document: DoclingDocument) -> None:
    """Rejoin a paragraph, list item or code block a page break cut in two.

    docling reads each page on its own, so text that simply carries on onto
    the next page comes out as two items — two Markdown paragraphs, or two
    separate code fences — with a break where the PDF has none. This joins
    the last item of a page with the first item of the next when the second
    is plainly the same content carrying on:

    - a paragraph or list item cut mid-sentence: it ends in a letter, digit,
      comma or hyphen (no full stop or colon), and the next page resumes in
      the same column with ordinary text. A word hyphenated across the break
      ("permi-" + "te") is rejoined without the hyphen;
    - a list item whose paragraph continues: the next page resumes indented
      like the bullet's own text, even if the cut fell right after a full stop;
    - a code block followed directly by another one on the next page.

    A margin-column item read after the main column on the previous page is
    looked past (it is not where the cut text ends). Anything else — a
    heading, a picture, a different column — is a real break and kept.
    """
    sequence = [
        item
        for item, _ in document.iterate_items()
        if isinstance(item, DocItem)
        and item.prov
        and item.label not in _FURNITURE
        and not is_inside_figure(document, item)
    ]
    absorbed: list[NodeItem] = []
    previous: list[DocItem] = []
    previous_page = -1
    for page_no, page_items in groupby(sequence, key=lambda item: item.prov[0].page_no):
        items = list(page_items)
        if previous and page_no == previous_page + 1:
            head = items[0]
            tail = _last_in_column(previous, head)
            if isinstance(tail, TextItem) and isinstance(head, TextItem) and _continues(tail, head):
                _merge(tail, head)
                absorbed.append(head)
                # A block cut across several pages keeps absorbing into the
                # same tail: this page's "last item" may be the one just merged.
                items[0] = tail
        previous, previous_page = items, page_no

    if absorbed:
        document.delete_items(node_items=absorbed)


def _last_in_column(items: list[DocItem], head: DocItem) -> DocItem | None:
    left = head.prov[0].bbox.l
    for item in reversed(items):
        if item.prov[0].bbox.l <= left + _MARGIN_POINTS:
            return item
    return None


def _continues(tail: TextItem, head: TextItem) -> bool:
    if isinstance(tail, CodeItem) or isinstance(head, CodeItem):
        return isinstance(tail, CodeItem) and isinstance(head, CodeItem)
    is_bullet = isinstance(tail, ListItem)
    if not (is_bullet or tail.label == DocItemLabel.TEXT):
        return False
    if head.label != DocItemLabel.TEXT or not tail.text:
        return False
    tail_left, head_left = tail.prov[0].bbox.l, head.prov[0].bbox.l
    if not tail_left - 2 <= head_left <= tail_left + _SAME_COLUMN_POINTS:
        return False
    last = tail.text.rstrip()[-1:]
    cut_mid_sentence = last.isalnum() or last in ",-"
    bullet_carries_on = is_bullet and head_left > tail_left + _BULLET_INDENT_POINTS
    return cut_mid_sentence or bullet_carries_on


def _merge(tail: TextItem, head: TextItem) -> None:
    if isinstance(tail, CodeItem):
        tail.text = f"{tail.text}\n{head.text}"
    elif tail.text.endswith("-") and tail.text[-2:-1].isalpha() and head.text[:1].islower():
        tail.text = tail.text[:-1] + head.text
    else:
        tail.text = f"{tail.text.rstrip()} {head.text.lstrip()}"
    tail.prov.extend(head.prov)
