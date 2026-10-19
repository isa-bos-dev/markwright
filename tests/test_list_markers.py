from docling_core.types.doc.document import DoclingDocument

from markwright.core.list_markers import fix_broken_list_markers, keep_original_list_numbers

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


# --- A list whose printed numbers aren't 1, 2, 3 keeps them ---


def _numbered_list(doc: DoclingDocument, entries: list[tuple[str, str]]):
    group = doc.add_list_group()
    return [
        doc.add_list_item(text=text, parent=group, enumerated=bool(marker), marker=marker)
        for marker, text in entries
    ]


def test_a_table_of_contents_keeps_its_section_numbers() -> None:
    doc = DoclingDocument(name="test")
    _numbered_list(
        doc,
        [
            ("1.", "Kali Linux....... 7"),
            ("1.1.", "Reverse Engineering....... 7"),
            ("", "3.Disassemblers....... 17"),
        ],
    )

    keep_original_list_numbers(doc)

    assert doc.export_to_markdown().splitlines() == [
        "- 1. Kali Linux....... 7",
        "- 1.1. Reverse Engineering....... 7",
        "- 3. Disassemblers....... 17",
    ]


def test_section_numbers_printed_without_a_final_dot_are_kept_too() -> None:
    """ISO 27002's controls in 3.1 are listed as "12.1", "12.1.1", "12.2"."""
    doc = DoclingDocument(name="test")
    _numbered_list(
        doc, [("12.1", "Requerimientos."), ("12.1.1", "Análisis."), ("12.2", "Proceso.")]
    )

    keep_original_list_numbers(doc)

    assert doc.export_to_markdown().splitlines() == [
        "- 12.1 Requerimientos.",
        "- 12.1.1 Análisis.",
        "- 12.2 Proceso.",
    ]


def test_a_plain_sequential_list_is_left_to_the_default_numbering() -> None:
    doc = DoclingDocument(name="test")
    items = _numbered_list(doc, [("1)", "Primero."), ("2)", "Segundo.")])

    keep_original_list_numbers(doc)

    assert [(item.marker, item.text, item.enumerated) for item in items] == [
        ("1)", "Primero.", True),
        ("2)", "Segundo.", True),
    ]


def test_a_list_where_some_item_has_no_number_is_left_untouched() -> None:
    doc = DoclingDocument(name="test")
    items = _numbered_list(doc, [("1.1.", "Con número."), ("", "Sin número.")])

    keep_original_list_numbers(doc)

    assert items[0].marker == "1.1."
    assert items[1].text == "Sin número."


def test_a_decimal_at_the_start_of_the_text_is_not_taken_for_a_glued_number() -> None:
    doc = DoclingDocument(name="test")
    items = _numbered_list(doc, [("2.", "Uno."), ("", "3.5 GHz de frecuencia.")])

    keep_original_list_numbers(doc)

    assert items[1].text == "3.5 GHz de frecuencia."
