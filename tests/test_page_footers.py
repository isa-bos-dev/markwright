from docling_core.types.doc import (
    BoundingBox,
    CodeItem,
    ContentLayer,
    DocItemLabel,
    ProvenanceItem,
)
from docling_core.types.doc.document import DoclingDocument

from markwright.core.page_footers import restore_misread_footers


def _prov(page_no: int, top: float, left: float = 57) -> ProvenanceItem:
    return ProvenanceItem(
        page_no=page_no, bbox=BoundingBox(l=left, t=top, r=500, b=top - 8), charspan=(0, 1)
    )


def _footer(doc: DoclingDocument, text: str, page_no: int, left: float = 57):
    return doc.add_text(
        label=DocItemLabel.PAGE_FOOTER,
        text=text,
        prov=_prov(page_no, 110, left),
        content_layer=ContentLayer.FURNITURE,
    )


def _markdown(doc: DoclingDocument) -> str:
    return doc.export_to_markdown(escape_html=False)


# --- A line docling took for a footer, printed only once, is content ---


def test_a_one_off_footer_line_indented_like_code_comes_back_as_code() -> None:
    """3.2, page 8: the SQL example's last line sits at the very bottom."""
    doc = DoclingDocument(name="test")
    doc.add_code(text="SELECT * FROM clientes", prov=_prov(8, 500, left=71))
    doc.add_text(label=DocItemLabel.TEXT, text="La consulta podría ser:", prov=_prov(8, 200))
    _footer(doc, '"SELECT count(*) FROM usuarios WHERE user = \'" + pUser', 8, left=71)

    restore_misread_footers(doc)

    codes = [item.text for item, _ in doc.iterate_items() if isinstance(item, CodeItem)]
    assert codes == [
        "SELECT * FROM clientes",
        '"SELECT count(*) FROM usuarios WHERE user = \'" + pUser',
    ]
    assert _markdown(doc).index("La consulta podría ser:") < _markdown(doc).index("pUser")


def test_a_one_off_footer_of_prose_comes_back_as_a_paragraph() -> None:
    """Page 2's licence notice, printed at the bottom of that page only."""
    doc = DoclingDocument(name="test")
    _footer(doc, "Los textos e imágenes publicados en esta obra están sujetos a una licencia.", 2)

    restore_misread_footers(doc)

    assert _markdown(doc) == (
        "Los textos e imágenes publicados en esta obra están sujetos a una licencia."
    )


def test_a_code_like_footer_not_indented_like_any_code_block_is_prose() -> None:
    doc = DoclingDocument(name="test")
    doc.add_code(text="x = 1;", prov=_prov(1, 500, left=71))
    _footer(doc, "Licencia (FUOC). Fundación para la Universitat Oberta.", 2, left=59)

    restore_misread_footers(doc)

    assert [item.text for item, _ in doc.iterate_items() if isinstance(item, CodeItem)] == [
        "x = 1;"
    ]
    assert "Licencia (FUOC)." in _markdown(doc)


# --- A real footer stays out of the text ---


def test_a_footer_repeated_on_several_pages_is_kept_out() -> None:
    doc = DoclingDocument(name="test")
    for page_no in (1, 2, 3):
        _footer(doc, f"Manual de usuario · página {page_no}", page_no)

    restore_misread_footers(doc)

    assert _markdown(doc) == ""


def test_a_bare_page_number_is_kept_out() -> None:
    doc = DoclingDocument(name="test")
    _footer(doc, "12", 12)

    restore_misread_footers(doc)

    assert _markdown(doc) == ""
