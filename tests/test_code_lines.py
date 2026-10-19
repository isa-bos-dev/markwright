from docling_core.types.doc import BoundingBox, DocItemLabel, PictureItem, ProvenanceItem
from docling_core.types.doc.document import DoclingDocument
from PIL import Image

from markwright.core.code_lines import restore_code_blocks

_PROV = ProvenanceItem(page_no=1, bbox=BoundingBox(l=0, t=100, r=50, b=0), charspan=(0, 1))


class _FakeRegions:
    """A PDF whose text layer in every region reads ``text``."""

    def __init__(self, text: str) -> None:
        self._text = text
        self.read: list[tuple[int, BoundingBox]] = []
        self.rendered: list[tuple[int, BoundingBox]] = []

    def text(self, page_no: int, bbox: BoundingBox) -> str:
        self.read.append((page_no, bbox))
        return self._text

    def image(self, page_no: int, bbox: BoundingBox) -> Image.Image:
        self.rendered.append((page_no, bbox))
        return Image.new("RGB", (20, 10), "white")


def _code(doc: DoclingDocument, text: str):
    return doc.add_code(text=text, prov=_PROV)


# --- A block with a real text layer gets its line breaks back ---


def test_line_breaks_come_back_from_the_pdf_text_layer() -> None:
    doc = DoclingDocument(name="test")
    item = _code(doc, "if (x) { y = 1; }")

    restore_code_blocks(doc, _FakeRegions("if (x) {\r\n y = 1; \r\n}"))

    assert item.text == "if (x) {\n y = 1;\n}"


def test_pdfium_hyphenation_marks_are_not_treated_as_content() -> None:
    doc = DoclingDocument(name="test")
    item = _code(doc, "run --verbose")

    restore_code_blocks(doc, _FakeRegions("run ￾\n--verbose"))

    assert item.text == "run\n--verbose"


def test_the_region_is_read_from_the_blocks_own_page_and_box() -> None:
    doc = DoclingDocument(name="test")
    _code(doc, "a b")
    regions = _FakeRegions("a\nb")

    restore_code_blocks(doc, regions)

    assert regions.read == [(1, _PROV.bbox)]


def test_a_region_whose_text_differs_from_doclings_is_left_alone() -> None:
    """A region that also caught a neighbouring line must not leak it in."""
    doc = DoclingDocument(name="test")
    item = _code(doc, "gcc ejemplo.c -o ejemplo")

    restore_code_blocks(doc, _FakeRegions("Ejemplo:\ngcc ejemplo.c -o ejemplo"))

    assert item.text == "gcc ejemplo.c -o ejemplo"
    assert doc.pictures == []


# --- A block OCR'd from a screenshot goes back to being that image ---


def test_a_block_without_text_layer_is_replaced_by_the_image_of_its_region() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.TEXT, text="Antes.")
    _code(doc, "ejemplo.c 1 #include <stdio.h) 2 int main() {")
    doc.add_text(label=DocItemLabel.TEXT, text="Después.")
    regions = _FakeRegions("")

    restore_code_blocks(doc, regions)

    assert doc.texts and all(item.label != DocItemLabel.CODE for item in doc.texts)
    assert regions.rendered == [(1, _PROV.bbox)]
    body = [child.resolve(doc) for child in doc.body.children]
    assert [type(node).__name__ for node in body] == ["TextItem", "PictureItem", "TextItem"]
    picture = body[1]
    assert isinstance(picture, PictureItem)
    assert picture.image is not None
    assert picture.prov == [_PROV]


def test_non_code_items_are_never_touched() -> None:
    doc = DoclingDocument(name="test")
    item = doc.add_text(label=DocItemLabel.TEXT, text="un párrafo", prov=_PROV)

    restore_code_blocks(doc, _FakeRegions(""))

    assert item.text == "un párrafo"
    assert doc.pictures == []
