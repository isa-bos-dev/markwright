from docling_core.types.doc import BoundingBox, DocItemLabel, ProvenanceItem
from docling_core.types.doc.document import DoclingDocument

from markwright.core.code_lines import restore_code_line_breaks

_PROV = ProvenanceItem(page_no=1, bbox=BoundingBox(l=0, t=100, r=50, b=0), charspan=(0, 1))


def _code(doc: DoclingDocument, text: str):
    return doc.add_code(text=text, prov=_PROV)


def test_line_breaks_come_back_from_the_pdf_text_layer() -> None:
    doc = DoclingDocument(name="test")
    item = _code(doc, "if (x) { y = 1; }")

    restore_code_line_breaks(doc, lambda page_no, bbox: "if (x) {\r\n y = 1; \r\n}")

    assert item.text == "if (x) {\n y = 1;\n}"


def test_a_block_without_text_layer_such_as_an_ocred_screenshot_is_left_alone() -> None:
    doc = DoclingDocument(name="test")
    item = _code(doc, "#include <stdio.h)")

    restore_code_line_breaks(doc, lambda page_no, bbox: "")

    assert item.text == "#include <stdio.h)"


def test_a_region_whose_text_differs_from_doclings_is_left_alone() -> None:
    """A region that also caught a neighbouring line must not leak it in."""
    doc = DoclingDocument(name="test")
    item = _code(doc, "gcc ejemplo.c -o ejemplo")

    restore_code_line_breaks(doc, lambda page_no, bbox: "Ejemplo:\ngcc ejemplo.c -o ejemplo")

    assert item.text == "gcc ejemplo.c -o ejemplo"


def test_pdfium_hyphenation_marks_are_not_treated_as_content() -> None:
    doc = DoclingDocument(name="test")
    item = _code(doc, "run --verbose")

    restore_code_line_breaks(doc, lambda page_no, bbox: "run ￾\n--verbose")

    assert item.text == "run\n--verbose"


def test_the_region_is_read_from_the_blocks_own_page_and_box() -> None:
    doc = DoclingDocument(name="test")
    _code(doc, "a b")
    seen: list[tuple[int, BoundingBox]] = []

    def reader(page_no: int, bbox: BoundingBox) -> str:
        seen.append((page_no, bbox))
        return "a\nb"

    restore_code_line_breaks(doc, reader)

    assert seen == [(1, _PROV.bbox)]


def test_non_code_items_are_never_touched() -> None:
    doc = DoclingDocument(name="test")
    item = doc.add_text(label=DocItemLabel.TEXT, text="un párrafo", prov=_PROV)

    restore_code_line_breaks(doc, lambda page_no, bbox: "un\npárrafo")

    assert item.text == "un párrafo"
