from docling_core.types.doc import DocItemLabel
from docling_core.types.doc.document import DoclingDocument

from markwright.core.footnotes import relocate_footnotes

# --- A footnote paragraph on the same page as its reference gets relocated ---


def test_footnote_is_moved_to_immediately_follow_its_referencing_paragraph() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.TEXT, text="Primer párrafo, sin relación.")
    doc.add_text(label=DocItemLabel.TEXT, text="Un concepto importante en beneficio común 1 .")
    doc.add_text(label=DocItemLabel.TEXT, text="Párrafo intermedio que no debería moverse.")
    doc.add_text(label=DocItemLabel.TEXT, text="(1) Autor, A. (2020). Título de la fuente.")

    relocate_footnotes(doc)

    assert doc.export_to_markdown(escape_html=False) == (
        "Primer párrafo, sin relación.\n\n"
        "Un concepto importante en beneficio común<sup>1</sup> .\n\n"
        "(1) Autor, A. (2020). Título de la fuente.\n\n"
        "Párrafo intermedio que no debería moverse."
    )


def test_inline_marker_becomes_a_sup_tag_glued_to_the_preceding_word() -> None:
    doc = DoclingDocument(name="test")
    anchor = doc.add_text(label=DocItemLabel.TEXT, text="Una frase con una referencia 2 .")
    doc.add_text(label=DocItemLabel.TEXT, text="(2) Fuente de la referencia.")

    relocate_footnotes(doc)

    assert anchor.text == "Una frase con una referencia<sup>2</sup> ."


def test_marker_followed_by_a_comma_mid_sentence_is_also_detected() -> None:
    doc = DoclingDocument(name="test")
    anchor = doc.add_text(
        label=DocItemLabel.TEXT, text="Siguiendo el mantra de alguien 3 , es necesario seguir."
    )
    doc.add_text(label=DocItemLabel.TEXT, text="(3) Fuente de la cita.")

    relocate_footnotes(doc)

    assert anchor.text == "Siguiendo el mantra de alguien<sup>3</sup> , es necesario seguir."


def test_two_independent_footnotes_each_find_their_own_anchor() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.TEXT, text="Primera idea con una referencia 1 .")
    doc.add_text(label=DocItemLabel.TEXT, text="Segunda idea con otra referencia 2 .")
    doc.add_text(label=DocItemLabel.TEXT, text="(1) Primera fuente.")
    doc.add_text(label=DocItemLabel.TEXT, text="(2) Segunda fuente.")

    relocate_footnotes(doc)

    assert doc.export_to_markdown(escape_html=False) == (
        "Primera idea con una referencia<sup>1</sup> .\n\n"
        "(1) Primera fuente.\n\n"
        "Segunda idea con otra referencia<sup>2</sup> .\n\n"
        "(2) Segunda fuente."
    )


# --- No match found: nothing is touched ---


def test_footnote_with_no_matching_inline_marker_on_any_page_is_left_in_place() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.TEXT, text="Un párrafo cualquiera sin ninguna referencia.")
    doc.add_text(label=DocItemLabel.TEXT, text="(1) Una nota que no referencia nadie.")

    relocate_footnotes(doc)

    assert doc.export_to_markdown(escape_html=False) == (
        "Un párrafo cualquiera sin ninguna referencia.\n\n(1) Una nota que no referencia nadie."
    )


def test_a_number_that_only_appears_on_a_different_page_is_not_matched() -> None:
    from docling_core.types.doc import BoundingBox, ProvenanceItem

    doc = DoclingDocument(name="test")
    anchor = doc.add_text(
        label=DocItemLabel.TEXT,
        text="Una referencia 1 .",
        prov=ProvenanceItem(page_no=1, bbox=BoundingBox(l=0, t=0, r=10, b=10), charspan=(0, 10)),
    )
    doc.add_text(
        label=DocItemLabel.TEXT,
        text="(1) Nota en otra página.",
        prov=ProvenanceItem(page_no=2, bbox=BoundingBox(l=0, t=0, r=10, b=10), charspan=(0, 10)),
    )

    relocate_footnotes(doc)

    assert anchor.text == "Una referencia 1 ."


def test_a_document_with_no_footnote_like_paragraphs_is_left_untouched() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.TEXT, text="Texto normal.")
    doc.add_text(label=DocItemLabel.TEXT, text="Más texto normal.")

    relocate_footnotes(doc)  # must not raise

    assert doc.export_to_markdown(escape_html=False) == "Texto normal.\n\nMás texto normal."


def test_a_detached_footnote_with_no_parent_is_skipped_instead_of_crashing() -> None:
    doc = DoclingDocument(name="test")
    anchor = doc.add_text(label=DocItemLabel.TEXT, text="Una referencia 1 .")
    footnote = doc.add_text(label=DocItemLabel.TEXT, text="(1) Una fuente.")
    footnote.parent = None

    relocate_footnotes(doc)  # must not raise even though the move is skipped

    assert anchor.text == "Una referencia<sup>1</sup> ."
