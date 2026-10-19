from docling_core.types.doc import BoundingBox, DocItemLabel, ProvenanceItem
from docling_core.types.doc.document import DoclingDocument

from markwright.core.page_breaks import join_across_page_breaks

_BODY_LEFT = 56.7
_BULLET_TEXT_LEFT = 73.7


def _prov(page_no: int, top: float, left: float = _BODY_LEFT) -> ProvenanceItem:
    return ProvenanceItem(
        page_no=page_no, bbox=BoundingBox(l=left, t=top, r=397, b=top - 10), charspan=(0, 1)
    )


def _text(doc: DoclingDocument, text: str, page_no: int, top: float, left: float = _BODY_LEFT):
    return doc.add_text(label=DocItemLabel.TEXT, text=text, prov=_prov(page_no, top, left))


def _bullet(doc: DoclingDocument, group, text: str, page_no: int, top: float):
    return doc.add_list_item(text=text, parent=group, prov=_prov(page_no, top))


def _paragraphs(doc: DoclingDocument) -> list[str]:
    return doc.export_to_markdown(escape_html=False).split("\n\n")


# --- Text cut mid-sentence by a page break is rejoined ---


def test_a_paragraph_cut_mid_sentence_continues_on_the_same_line() -> None:
    doc = DoclingDocument(name="test")
    _text(doc, "La explotación de la vulnerabilidad de", 8, 106)
    _text(doc, "inyección SQL y la toma de control.", 9, 771)

    join_across_page_breaks(doc)

    assert _paragraphs(doc) == [
        "La explotación de la vulnerabilidad de inyección SQL y la toma de control."
    ]


def test_a_list_item_cut_mid_sentence_takes_the_rest_of_its_sentence() -> None:
    """Sqlmap's bullet on page 8 carries on, indented, at the top of page 9."""
    doc = DoclingDocument(name="test")
    group = doc.add_list_group()
    _bullet(doc, group, "Sqlmap es una herramienta para la vulnerabilidad de", 8, 106)
    _text(doc, "inyección SQL. Sus características son:", 9, 771, left=_BULLET_TEXT_LEFT)

    join_across_page_breaks(doc)

    assert _paragraphs(doc) == [
        "- Sqlmap es una herramienta para la vulnerabilidad de inyección SQL."
        " Sus características son:"
    ]


def test_a_word_hyphenated_across_the_break_is_rejoined_without_the_hyphen() -> None:
    doc = DoclingDocument(name="test")
    group = doc.add_list_group()
    _bullet(doc, group, "rarun2: Por ejemplo, permi-", 20, 80)
    _text(doc, "te redirigir la entrada.", 21, 771, left=_BULLET_TEXT_LEFT)

    join_across_page_breaks(doc)

    assert _paragraphs(doc) == ["- rarun2: Por ejemplo, permite redirigir la entrada."]


def test_a_bullets_paragraph_continuing_after_a_full_stop_is_still_joined() -> None:
    """stepi's description ends a sentence at the page break, but the next
    page's indent shows it is still the same bullet's paragraph."""
    doc = DoclingDocument(name="test")
    group = doc.add_list_group()
    _bullet(doc, group, "stepi: ejecuta una instrucción en lenguaje máquina.", 25, 92)
    _text(doc, "Es el comando recomendado sin código fuente.", 26, 771, left=_BULLET_TEXT_LEFT)

    join_across_page_breaks(doc)

    assert _paragraphs(doc) == [
        "- stepi: ejecuta una instrucción en lenguaje máquina."
        " Es el comando recomendado sin código fuente."
    ]


def test_page_headers_between_the_two_halves_are_looked_past() -> None:
    doc = DoclingDocument(name="test")
    _text(doc, "Un párrafo que sigue", 1, 100)
    doc.add_text(label=DocItemLabel.PAGE_HEADER, text="© FUOC", prov=_prov(2, 790))
    _text(doc, "en la página siguiente.", 2, 771)

    join_across_page_breaks(doc)

    assert "Un párrafo que sigue en la página siguiente." in doc.export_to_markdown()


def test_a_margin_box_read_after_the_main_column_is_looked_past() -> None:
    doc = DoclingDocument(name="test")
    _text(doc, "Un párrafo de la columna principal que sigue", 1, 100)
    margin = _text(doc, "Disponible en: <http://ejemplo.org>", 1, 195, left=422.5)
    _text(doc, "en la página siguiente.", 2, 771)

    join_across_page_breaks(doc)

    paragraphs = _paragraphs(doc)
    assert paragraphs[0] == "Un párrafo de la columna principal que sigue en la página siguiente."
    assert margin.text in paragraphs[1]


# --- A real break is kept ---


def test_a_paragraph_ending_in_a_full_stop_is_kept_apart() -> None:
    doc = DoclingDocument(name="test")
    _text(doc, "Fin del párrafo.", 1, 100)
    _text(doc, "Nuevo párrafo.", 2, 771)

    join_across_page_breaks(doc)

    assert _paragraphs(doc) == ["Fin del párrafo.", "Nuevo párrafo."]


def test_a_paragraph_ending_in_a_colon_before_a_figure_is_kept_apart() -> None:
    doc = DoclingDocument(name="test")
    _text(doc, "Lo ejecutaremos de la forma siguiente:", 1, 100)
    _text(doc, "Otro texto.", 2, 771)

    join_across_page_breaks(doc)

    assert len(_paragraphs(doc)) == 2


def test_a_heading_at_the_top_of_the_next_page_is_kept_apart() -> None:
    doc = DoclingDocument(name="test")
    _text(doc, "Un texto sin punto final", 1, 100)
    doc.add_heading(text="2. Decompilers", prov=_prov(2, 771))

    join_across_page_breaks(doc)

    assert len(_paragraphs(doc)) == 2


def test_text_on_a_page_that_is_not_the_next_one_is_kept_apart() -> None:
    doc = DoclingDocument(name="test")
    _text(doc, "Un texto sin punto final", 1, 100)
    _text(doc, "en otra página lejana.", 3, 771)

    join_across_page_breaks(doc)

    assert len(_paragraphs(doc)) == 2


def test_a_plain_paragraph_after_a_bullet_ending_a_sentence_is_kept_apart() -> None:
    doc = DoclingDocument(name="test")
    group = doc.add_list_group()
    _bullet(doc, group, "Una viñeta terminada.", 1, 100)
    _text(doc, "Un párrafo normal, sin sangría.", 2, 771)

    join_across_page_breaks(doc)

    assert len(_paragraphs(doc)) == 2


# --- A code block cut by a page break is one block again ---


def test_a_code_block_continuing_on_the_next_page_becomes_one_block() -> None:
    doc = DoclingDocument(name="test")
    doc.add_code(text="void f() {\n int x;", prov=_prov(14, 692))
    doc.add_code(text=" x = 1;\n}", prov=_prov(15, 769))

    join_across_page_breaks(doc)

    codes = [item for item in doc.texts if item.label == DocItemLabel.CODE]
    assert [code.text for code in codes] == ["void f() {\n int x;\n x = 1;\n}"]


def test_a_block_spanning_three_pages_is_joined_into_one() -> None:
    doc = DoclingDocument(name="test")
    for page_no, line in ((1, "a"), (2, "b"), (3, "c")):
        doc.add_code(text=line, prov=_prov(page_no, 700))

    join_across_page_breaks(doc)

    assert [item.text for item in doc.texts] == ["a\nb\nc"]
