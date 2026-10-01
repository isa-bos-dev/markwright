from docling_core.types.doc import DocItemLabel, Formatting
from docling_core.types.doc.document import DoclingDocument
from pydantic import AnyUrl

from markwright.core.captions import italicize_captions


def test_a_caption_with_no_formatting_becomes_italic() -> None:
    doc = DoclingDocument(name="test")
    caption = doc.add_text(label=DocItemLabel.CAPTION, text="Fuente: Wikipedia")

    italicize_captions(doc)

    assert caption.formatting is not None
    assert caption.formatting.italic is True


def test_a_caption_with_a_hyperlink_still_exports_wrapped_in_italics() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(
        label=DocItemLabel.CAPTION, text="Fuente: algo", hyperlink=AnyUrl("http://example.com")
    )

    italicize_captions(doc)

    assert doc.export_to_markdown() == "[*Fuente: algo*](http://example.com/)"


def test_a_caption_with_existing_formatting_keeps_its_other_flags() -> None:
    doc = DoclingDocument(name="test")
    caption = doc.add_text(label=DocItemLabel.CAPTION, text="Fuente: algo")
    caption.formatting = Formatting(bold=True)

    italicize_captions(doc)

    assert caption.formatting.bold is True
    assert caption.formatting.italic is True


def test_a_non_caption_text_item_is_left_untouched() -> None:
    doc = DoclingDocument(name="test")
    text = doc.add_text(label=DocItemLabel.TEXT, text="Texto normal.")

    italicize_captions(doc)

    assert text.formatting is None
