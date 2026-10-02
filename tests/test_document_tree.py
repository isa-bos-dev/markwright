from docling_core.types.doc import DocItemLabel, GroupLabel
from docling_core.types.doc.document import DoclingDocument

from markwright.core.document_tree import move_item_after


def test_an_item_is_moved_to_immediately_follow_the_anchor() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.TEXT, text="AAA")
    doc.add_text(label=DocItemLabel.TEXT, text="BBB")
    item = doc.add_text(label=DocItemLabel.TEXT, text="CCC")
    anchor = doc.add_text(label=DocItemLabel.TEXT, text="DDD")

    move_item_after(doc, item=item, anchor=anchor)

    assert doc.export_to_markdown() == "AAA\n\nBBB\n\nDDD\n\nCCC"


def test_moving_several_items_in_reverse_order_keeps_their_relative_order() -> None:
    doc = DoclingDocument(name="test")
    anchor = doc.add_text(label=DocItemLabel.TEXT, text="Anchor")
    doc.add_text(label=DocItemLabel.TEXT, text="Unrelated")
    first = doc.add_text(label=DocItemLabel.TEXT, text="First")
    second = doc.add_text(label=DocItemLabel.TEXT, text="Second")

    move_item_after(doc, item=second, anchor=anchor)
    move_item_after(doc, item=first, anchor=anchor)

    assert doc.export_to_markdown() == "Anchor\n\nFirst\n\nSecond\n\nUnrelated"


def test_moving_an_item_into_a_different_parent_group_updates_its_own_back_reference() -> None:
    # Moving within the same parent (the only case exercised until a real
    # document caught this) never surfaces a stale item.parent — only moving
    # across groups does, because DoclingDocument's own tree validation
    # checks that every item's .parent actually matches where it now lives.
    doc = DoclingDocument(name="test")
    group = doc.add_group(label=GroupLabel.LIST)
    item = doc.add_text(label=DocItemLabel.LIST_ITEM, text="Inside the list group", parent=group)
    anchor = doc.add_text(label=DocItemLabel.TEXT, text="Top-level anchor")

    move_item_after(doc, item=item, anchor=anchor)

    assert item.parent is not None
    assert item.parent.cref == anchor.parent.cref
    assert doc.export_to_markdown() == "Top-level anchor\n\n- Inside the list group"


def test_an_item_with_no_parent_is_skipped_instead_of_crashing() -> None:
    doc = DoclingDocument(name="test")
    item = doc.add_text(label=DocItemLabel.TEXT, text="AAA")
    anchor = doc.add_text(label=DocItemLabel.TEXT, text="BBB")
    original_children = list(doc.body.children)
    item.parent = None

    move_item_after(doc, item=item, anchor=anchor)  # must not raise

    assert doc.body.children == original_children


def test_an_anchor_with_no_parent_is_also_skipped_instead_of_crashing() -> None:
    doc = DoclingDocument(name="test")
    item = doc.add_text(label=DocItemLabel.TEXT, text="AAA")
    anchor = doc.add_text(label=DocItemLabel.TEXT, text="BBB")
    original_children = list(doc.body.children)
    anchor.parent = None

    move_item_after(doc, item=item, anchor=anchor)  # must not raise

    assert doc.body.children == original_children
