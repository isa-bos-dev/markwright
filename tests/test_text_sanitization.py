from docling_core.types.doc import DocItemLabel
from docling_core.types.doc.document import DoclingDocument

from markwright.core.text_sanitization import fix_mangled_spaces


def test_a_mangled_space_character_is_replaced_with_a_normal_space() -> None:
    doc = DoclingDocument(name="test")
    item = doc.add_text(label=DocItemLabel.TEXT, text="periodismo￿de￿datos")

    fix_mangled_spaces(doc)

    assert item.text == "periodismo de datos"


def test_multiple_mangled_spaces_in_the_same_item_are_all_replaced() -> None:
    doc = DoclingDocument(name="test")
    item = doc.add_text(label=DocItemLabel.TEXT, text="g)￿Visualización￿de￿datos")

    fix_mangled_spaces(doc)

    assert item.text == "g) Visualización de datos"


def test_text_with_no_mangled_characters_is_left_untouched() -> None:
    doc = DoclingDocument(name="test")
    item = doc.add_text(label=DocItemLabel.TEXT, text="Texto normal sin problemas.")

    fix_mangled_spaces(doc)

    assert item.text == "Texto normal sin problemas."


def test_every_text_item_in_the_document_is_sanitized_not_just_the_first() -> None:
    doc = DoclingDocument(name="test")
    first = doc.add_text(label=DocItemLabel.TEXT, text="uno￿dos")
    second = doc.add_text(label=DocItemLabel.TEXT, text="tres￿cuatro")

    fix_mangled_spaces(doc)

    assert first.text == "uno dos"
    assert second.text == "tres cuatro"
