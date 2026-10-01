from docling_core.types.doc import DocItemLabel
from docling_core.types.doc.document import DoclingDocument

from markwright.core.footnotes import relocate_footnotes

# --- A footnote paragraph gets relocated to its marker ---


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


def test_marker_with_a_space_before_it_becomes_a_sup_tag_glued_to_the_word() -> None:
    doc = DoclingDocument(name="test")
    anchor = doc.add_text(label=DocItemLabel.TEXT, text="Una frase con una referencia 2 .")
    doc.add_text(label=DocItemLabel.TEXT, text="(2) Fuente de la referencia.")

    relocate_footnotes(doc)

    assert anchor.text == "Una frase con una referencia<sup>2</sup> ."


def test_marker_glued_directly_to_the_word_with_no_space_is_also_detected() -> None:
    # docling often drops the superscript's visual gap, so the digit ends up
    # glued straight onto the preceding word with no space at all.
    doc = DoclingDocument(name="test")
    anchor = doc.add_text(label=DocItemLabel.TEXT, text="Una frase con un concepto10 citado.")
    doc.add_text(label=DocItemLabel.TEXT, text="(10) Fuente de la cita.")

    relocate_footnotes(doc)

    assert anchor.text == "Una frase con un concepto<sup>10</sup> citado."


def test_marker_followed_by_a_comma_mid_sentence_is_also_detected() -> None:
    doc = DoclingDocument(name="test")
    anchor = doc.add_text(
        label=DocItemLabel.TEXT, text="Siguiendo el mantra de alguien 3 , es necesario seguir."
    )
    doc.add_text(label=DocItemLabel.TEXT, text="(3) Fuente de la cita.")

    relocate_footnotes(doc)

    assert anchor.text == "Siguiendo el mantra de alguien<sup>3</sup> , es necesario seguir."


# --- Sequential order disambiguates real markers from unrelated numbers ---


def test_two_independent_footnotes_each_find_their_own_anchor_in_order() -> None:
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


def test_an_unrelated_earlier_number_does_not_steal_a_later_footnotes_marker() -> None:
    # "2 habitaciones" here is unrelated prose, not footnote 2's marker — it
    # sits before footnote 1's own marker, so if order weren't enforced it
    # could wrongly get consumed first.
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.TEXT, text="El piso tiene 2 habitaciones y un balcón.")
    doc.add_text(label=DocItemLabel.TEXT, text="Primera idea con una referencia 1 .")
    doc.add_text(label=DocItemLabel.TEXT, text="Segunda idea con otra referencia 2 .")
    doc.add_text(label=DocItemLabel.TEXT, text="(1) Primera fuente.")
    doc.add_text(label=DocItemLabel.TEXT, text="(2) Segunda fuente.")

    relocate_footnotes(doc)

    markdown = doc.export_to_markdown(escape_html=False)
    assert "El piso tiene 2 habitaciones y un balcón." in markdown
    assert "Segunda idea con otra referencia<sup>2</sup> ." in markdown


def test_a_digit_glued_to_a_following_letter_is_not_mistaken_for_a_marker() -> None:
    # "tabla 3D" is a label, not a footnote reference — found against the
    # real sample PDF, where it wrongly stole footnote 3's match.
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.TEXT, text="Se puede representar como una tabla 3D aquí.")
    doc.add_text(label=DocItemLabel.TEXT, text="Un dato citado por alguien 3 , tal y como dijo.")
    doc.add_text(label=DocItemLabel.TEXT, text="(3) Fuente de la cita real.")

    relocate_footnotes(doc)

    markdown = doc.export_to_markdown(escape_html=False)
    assert "tabla 3D aquí." in markdown
    assert "Un dato citado por alguien<sup>3</sup> , tal y como dijo." in markdown


def test_a_digit_glued_via_a_hyphen_to_a_following_word_is_not_mistaken_for_a_marker() -> None:
    # "3-tuplas" is a compound term, not a footnote reference — also found
    # against the real sample PDF, where it wrongly stole footnote 3's match
    # even after the direct-letter guard above (there's a hyphen in between).
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.TEXT, text="Los datos son 3-tuplas de la forma [E1, R, E2].")
    doc.add_text(label=DocItemLabel.TEXT, text="Un dato citado por alguien 3 , tal y como dijo.")
    doc.add_text(label=DocItemLabel.TEXT, text="(3) Fuente de la cita real.")

    relocate_footnotes(doc)

    markdown = doc.export_to_markdown(escape_html=False)
    assert "Los datos son 3-tuplas de la forma" in markdown
    assert "Un dato citado por alguien<sup>3</sup> , tal y como dijo." in markdown


def test_an_exponent_written_as_plain_text_is_not_mistaken_for_a_marker() -> None:
    # "10^3" is exponent notation, not a footnote reference — also found
    # against the real sample PDF.
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.TEXT, text="Puede tomar 2^10 ≈ 10^3 valores diferentes.")
    doc.add_text(label=DocItemLabel.TEXT, text="Un dato citado por alguien 3 , tal y como dijo.")
    doc.add_text(label=DocItemLabel.TEXT, text="(3) Fuente de la cita real.")

    relocate_footnotes(doc)

    markdown = doc.export_to_markdown(escape_html=False)
    assert "2^10 ≈ 10^3 valores diferentes." in markdown
    assert "Un dato citado por alguien<sup>3</sup> , tal y como dijo." in markdown


def test_a_number_at_the_very_start_of_a_paragraph_is_not_mistaken_for_a_marker() -> None:
    # "1. Primer punto" looks like a numbered list item, not a footnote
    # reference — a real marker always sits mid-sentence, referring back to
    # something already said.
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.TEXT, text="1. Primer punto de una lista cualquiera.")
    doc.add_text(label=DocItemLabel.TEXT, text="Una frase con una referencia real 1 .")
    doc.add_text(label=DocItemLabel.TEXT, text="(1) Fuente de la referencia real.")

    relocate_footnotes(doc)

    markdown = doc.export_to_markdown(escape_html=False)
    assert "1. Primer punto de una lista cualquiera." in markdown
    assert "Una frase con una referencia real<sup>1</sup> ." in markdown


# --- No match found: nothing is touched ---


def test_footnote_with_no_matching_marker_anywhere_is_left_in_place() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.TEXT, text="Un párrafo cualquiera sin ninguna referencia.")
    doc.add_text(label=DocItemLabel.TEXT, text="(1) Una nota que no referencia nadie.")

    relocate_footnotes(doc)

    assert doc.export_to_markdown(escape_html=False) == (
        "Un párrafo cualquiera sin ninguna referencia.\n\n(1) Una nota que no referencia nadie."
    )


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
