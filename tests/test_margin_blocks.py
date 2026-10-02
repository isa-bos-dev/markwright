from docling_core.types.doc import BoundingBox, DocItemLabel, ProvenanceItem
from docling_core.types.doc.document import DoclingDocument

from markwright.core.margin_blocks import relocate_margin_blocks


def _prov(page_no: int, top: float) -> ProvenanceItem:
    return ProvenanceItem(
        page_no=page_no, bbox=BoundingBox(l=0, t=top, r=10, b=top - 5), charspan=(0, 10)
    )


def _add(doc: DoclingDocument, label: DocItemLabel, text: str, page_no: int, top: float):
    return doc.add_text(label=label, text=text, prov=_prov(page_no, top))


def test_a_margin_block_moves_after_the_nearest_main_column_paragraph() -> None:
    doc = DoclingDocument(name="test")
    far = _add(doc, DocItemLabel.TEXT, "Primer párrafo lejano.", 1, 900)
    near = _add(doc, DocItemLabel.TEXT, "Segundo párrafo, el más cercano.", 1, 574)
    third = _add(doc, DocItemLabel.TEXT, "Tercer párrafo.", 1, 300)
    header = _add(doc, DocItemLabel.SECTION_HEADER, "No obstante…", 1, 568)
    body = _add(doc, DocItemLabel.TEXT, "Cuerpo de la nota al margen.", 1, 547)

    relocate_margin_blocks(doc)

    markdown = doc.export_to_markdown()
    assert markdown.index(far.text) < markdown.index(near.text)
    assert markdown.index(near.text) < markdown.index(header.text)
    assert markdown.index(header.text) < markdown.index(body.text)
    assert markdown.index(body.text) < markdown.index(third.text)


def test_multiple_margin_sub_blocks_each_anchor_independently() -> None:
    doc = DoclingDocument(name="test")
    _add(doc, DocItemLabel.TEXT, "Extracción de datos de documentos de texto.", 1, 571)
    _add(doc, DocItemLabel.TEXT, "Formularios.", 1, 402)
    header_a = _add(doc, DocItemLabel.SECTION_HEADER, "Herramientas de extracción", 1, 567)
    body_a = _add(doc, DocItemLabel.TEXT, "Tabula, Tesseract.", 1, 527)
    header_b = _add(doc, DocItemLabel.SECTION_HEADER, "Herramientas de formularios", 1, 398)
    body_b = _add(doc, DocItemLabel.TEXT, "Google Forms, LimeSurvey.", 1, 367)

    relocate_margin_blocks(doc)

    markdown = doc.export_to_markdown()
    assert markdown.index("Extracción de datos") < markdown.index(header_a.text)
    assert markdown.index(header_a.text) < markdown.index(body_a.text)
    assert markdown.index(body_a.text) < markdown.index("Formularios.")
    assert markdown.index("Formularios.") < markdown.index(header_b.text)
    assert markdown.index(header_b.text) < markdown.index(body_b.text)


def test_a_footnote_shaped_item_inside_a_margin_run_is_left_for_relocate_footnotes() -> None:
    doc = DoclingDocument(name="test")
    anchor = _add(doc, DocItemLabel.TEXT, "Párrafo con una referencia.", 1, 574)
    header = _add(doc, DocItemLabel.SECTION_HEADER, "No obstante…", 1, 568)
    body = _add(doc, DocItemLabel.TEXT, "Cuerpo de la nota.", 1, 547)
    footnote = _add(doc, DocItemLabel.TEXT, "(2) Fuente citada.", 1, 364)

    relocate_margin_blocks(doc)

    markdown = doc.export_to_markdown()
    assert markdown.index(anchor.text) < markdown.index(header.text)
    assert markdown.index(header.text) < markdown.index(body.text)
    # the footnote-shaped item was not moved at all
    assert markdown.index(footnote.text) > markdown.index(body.text)


def test_a_margin_run_that_is_only_a_footnote_is_entirely_skipped() -> None:
    doc = DoclingDocument(name="test")
    _add(doc, DocItemLabel.TEXT, "Párrafo principal.", 1, 400)
    # Higher top than the preceding item — a real column jump, so this is
    # seen as a margin run (not just normal top-to-bottom continuation).
    footnote = _add(doc, DocItemLabel.TEXT, "(1) Fuente citada.", 1, 800)

    relocate_margin_blocks(doc)  # must not raise, nothing to move

    assert doc.export_to_markdown() == "Párrafo principal.\n\n(1) Fuente citada."
    assert footnote.text == "(1) Fuente citada."


def test_a_page_with_no_column_jump_is_left_untouched() -> None:
    doc = DoclingDocument(name="test")
    _add(doc, DocItemLabel.TEXT, "Primero.", 1, 800)
    _add(doc, DocItemLabel.TEXT, "Segundo.", 1, 600)
    _add(doc, DocItemLabel.TEXT, "Tercero.", 1, 400)

    relocate_margin_blocks(doc)

    assert doc.export_to_markdown() == "Primero.\n\nSegundo.\n\nTercero."


def test_page_headers_footers_and_captions_do_not_interfere_with_detection() -> None:
    doc = DoclingDocument(name="test")
    _add(doc, DocItemLabel.PAGE_HEADER, "Encabezado de página", 1, 999)
    _add(doc, DocItemLabel.PAGE_FOOTER, "Pie de página", 1, 10)
    anchor = _add(doc, DocItemLabel.TEXT, "Párrafo principal.", 1, 574)
    _add(doc, DocItemLabel.CAPTION, "Pie de una imagen.", 1, 900)
    header = _add(doc, DocItemLabel.SECTION_HEADER, "Nota al margen", 1, 568)

    relocate_margin_blocks(doc)

    markdown = doc.export_to_markdown()
    assert markdown.index(anchor.text) < markdown.index(header.text)


def test_items_without_provenance_are_ignored() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.TEXT, text="Sin posición conocida.")
    _add(doc, DocItemLabel.TEXT, "Con posición.", 1, 500)

    relocate_margin_blocks(doc)  # must not raise

    assert doc.export_to_markdown() == "Sin posición conocida.\n\nCon posición."


def test_pages_are_handled_independently() -> None:
    doc = DoclingDocument(name="test")
    _add(doc, DocItemLabel.TEXT, "Página 1, párrafo principal.", 1, 700)
    header1 = _add(doc, DocItemLabel.SECTION_HEADER, "Nota página 1", 1, 690)
    _add(doc, DocItemLabel.TEXT, "Página 2, párrafo principal.", 2, 700)
    header2 = _add(doc, DocItemLabel.SECTION_HEADER, "Nota página 2", 2, 690)

    relocate_margin_blocks(doc)

    markdown = doc.export_to_markdown()
    assert markdown.index("Página 1, párrafo principal.") < markdown.index(header1.text)
    assert markdown.index(header1.text) < markdown.index("Página 2, párrafo principal.")
    assert markdown.index("Página 2, párrafo principal.") < markdown.index(header2.text)
