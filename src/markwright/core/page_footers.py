from __future__ import annotations

import re
from collections import Counter
from typing import TYPE_CHECKING

from docling_core.types.doc import CodeItem, ContentLayer, DocItemLabel, TextItem

from markwright.core.document_tree import move_item_after

if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument

# A code block starts within this much of another one's left edge.
_SAME_INDENT_POINTS = 2.0
# Characters plain prose almost never has but a line of code nearly always does.
_CODE_CHARACTERS = re.compile(r"[(){};=+*\"]")


def restore_misread_footers(document: DoclingDocument) -> None:
    """Put back text docling took for a page footer when it is not one.

    docling labels whatever sits at the very bottom of a page as a footer and
    leaves it out of the Markdown. A real footer repeats from page to page
    (the same line, or one only its page number changes in); the last line
    of a code example or a page's licence notice is printed once. Such a
    one-off "footer" is real content and goes back into the text, as code
    when it is indented like the document's code blocks and reads like code
    — otherwise as a paragraph.
    """
    footers = [item for item in document.texts if item.label == DocItemLabel.PAGE_FOOTER]
    pages_per_shape = Counter(
        shape for shape, _ in {(_shape(item.text), _page(item)) for item in footers}
    )
    code_lefts = [
        item.prov[0].bbox.l for item in document.texts if isinstance(item, CodeItem) and item.prov
    ]

    code_lines: list[TextItem] = []
    for item in footers:
        if pages_per_shape[_shape(item.text)] > 1 or not re.search(r"[^\W\d_]", item.text):
            continue
        if _reads_as_code(item, code_lefts):
            code_lines.append(item)
        else:
            item.label = DocItemLabel.TEXT
            item.content_layer = ContentLayer.BODY

    # A code line becomes a real CodeItem (a different class, not just a
    # label), so it is added in the footer's place and the footer removed.
    for item in code_lines:
        if item.parent is None:
            continue
        parent = item.parent.resolve(document)
        code = document.add_code(text=item.text, prov=item.prov[0], parent=parent)
        move_item_after(document, item=code, anchor=item)
    if code_lines:
        document.delete_items(node_items=[*code_lines])


def _shape(text: str) -> str:
    return re.sub(r"\d+", "#", " ".join(text.split()))


def _page(item: TextItem) -> int:
    return item.prov[0].page_no if item.prov else 0


def _reads_as_code(item: TextItem, code_lefts: list[float]) -> bool:
    if not item.prov or not _CODE_CHARACTERS.search(item.text):
        return False
    left = item.prov[0].bbox.l
    return any(abs(left - code_left) <= _SAME_INDENT_POINTS for code_left in code_lefts)
