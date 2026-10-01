from docling_core.types.doc.document import DoclingDocument

from markwright.core.list_markers import fix_broken_list_markers

# --- A number-paren marker swallowed by docling is reclassified ---


def test_a_digit_marker_followed_by_the_mangled_space_character_is_fixed() -> None:
    doc = DoclingDocument(name="test")
    group = doc.add_list_group()
    item = doc.add_list_item(
        text="1)￿Fusión: texto del punto.", parent=group, enumerated=False, marker=""
    )

    fix_broken_list_markers(doc)

    assert item.enumerated is True
    assert item.marker == "1)"
    assert item.text == "Fusión: texto del punto."


def test_a_digit_marker_followed_by_a_normal_space_is_also_fixed() -> None:
    doc = DoclingDocument(name="test")
    group = doc.add_list_group()
    item = doc.add_list_item(
        text="2) Selección: texto del punto.", parent=group, enumerated=False, marker=""
    )

    fix_broken_list_markers(doc)

    assert item.enumerated is True
    assert item.marker == "2)"
    assert item.text == "Selección: texto del punto."


def test_a_letter_marker_is_also_fixed() -> None:
    doc = DoclingDocument(name="test")
    group = doc.add_list_group()
    item = doc.add_list_item(text="a)￿Primera opción.", parent=group, enumerated=False, marker="")

    fix_broken_list_markers(doc)

    assert item.enumerated is True
    assert item.marker == "a)"
    assert item.text == "Primera opción."


# --- Already-correct items are left untouched ---


def test_an_item_already_correctly_enumerated_by_docling_is_left_untouched() -> None:
    doc = DoclingDocument(name="test")
    group = doc.add_list_group()
    item = doc.add_list_item(
        text="Ficheros simples: ya viene bien.", parent=group, enumerated=True, marker="1)"
    )

    fix_broken_list_markers(doc)

    assert item.enumerated is True
    assert item.marker == "1)"
    assert item.text == "Ficheros simples: ya viene bien."


def test_an_unordered_list_item_with_no_marker_shape_is_left_untouched() -> None:
    doc = DoclingDocument(name="test")
    group = doc.add_list_group()
    item = doc.add_list_item(
        text="Simples: datos atómicos indivisibles.", parent=group, enumerated=False, marker=""
    )

    fix_broken_list_markers(doc)

    assert item.enumerated is False
    assert item.marker == ""
    assert item.text == "Simples: datos atómicos indivisibles."
