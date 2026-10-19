from __future__ import annotations

from itertools import groupby
from typing import TYPE_CHECKING

from docling_core.types.doc import CodeItem, DocItem, DocItemLabel, ListItem, TextItem

from markwright.core.document_tree import is_inside_figure, move_item_before

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


def split_joins_across_columns(document: DoclingDocument) -> None:
    """Undo docling's own page-break join where it glued two different columns.

    docling already joins some paragraphs across a page break itself, and
    can pick the wrong pair: the end of a margin box ("Enlaces recomendados")
    glued to the body paragraph opening the next page. The two parts of such
    an item start far apart horizontally; each goes back to being its own
    item, placed where its page starts in the reading order.
    """
    for item in list(document.texts):
        if isinstance(item, CodeItem) or item.label != DocItemLabel.TEXT or len(item.prov) < 2:
            continue
        if item.parent is None or item.prov[-1].charspan[1] != len(item.text):
            continue  # text already edited: its charspans no longer index it
        cuts = [
            index
            for index in range(1, len(item.prov))
            if abs(item.prov[index].bbox.l - item.prov[index - 1].bbox.l) > _SAME_COLUMN_POINTS
        ]
        if not cuts:
            continue
        text, provs = item.text, list(item.prov)
        bounds = [0, *cuts, len(provs)]
        parts = [provs[start:end] for start, end in zip(bounds, bounds[1:], strict=False)]
        item.text = text[: parts[0][-1].charspan[1]].rstrip()
        item.orig = item.text
        item.prov = parts[0]
        parent = item.parent.resolve(document)
        for part in parts[1:]:
            rest = text[part[0].charspan[0] : part[-1].charspan[1]].strip()
            new = document.add_text(label=DocItemLabel.TEXT, text=rest, prov=part[0], parent=parent)
            new.prov.extend(part[1:])
            following = _first_on_page(document, part[0].page_no, exclude=new)
            if following is not None:
                move_item_before(document, item=new, anchor=following)


def _first_on_page(document: DoclingDocument, page_no: int, exclude: DocItem) -> DocItem | None:
    for node, _ in document.iterate_items():
        if (
            node is exclude
            or is_inside_figure(document, node)
            or not isinstance(node, DocItem)
            or not node.prov
        ):
            continue
        if node.prov[0].page_no >= page_no:
            return node
    return None


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
