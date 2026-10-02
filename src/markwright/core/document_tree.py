from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument
    from docling_core.types.doc.items.node import NodeItem


def move_item_after(document: DoclingDocument, *, item: NodeItem, anchor: NodeItem) -> None:
    """Move an existing item to immediately follow another, in the body tree.

    ``document.texts`` is a flat list in *insertion* order — it does not
    reflect export/reading order, which lives in ``document.body.children``
    (and nested groups) as ``RefItem``s. Moving an item means editing that
    list directly: docling_core's own ``insert_item_after_sibling`` is for
    *new* items only (it appends to the typed list, so passing an existing
    item would duplicate it).
    """
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
    # Moving to a *different* parent group (not just a new position within
    # the same one, the only case this went untested against until a real
    # document caught it) must update the item's own back-reference too, or
    # DoclingDocument's own tree validation rejects the result as corrupt.
    item.parent = new_parent.get_ref()
