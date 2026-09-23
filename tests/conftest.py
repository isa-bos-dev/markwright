from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from docling.datamodel.base_models import ConversionStatus, DoclingComponentType
from docling.datamodel.document import ErrorItem, FailureCategory
from docling_core.types.doc import DocItemLabel, ImageRef
from docling_core.types.doc.document import DoclingDocument
from pypdf import PdfWriter


@pytest.fixture
def plain_pdf_factory(tmp_path: Path) -> Callable[..., Path]:
    """Return a factory that writes a tiny unencrypted PDF and returns its path."""

    def _make(name: str = "input.pdf") -> Path:
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        path = tmp_path / name
        with path.open("wb") as f:
            writer.write(f)
        return path

    return _make


@pytest.fixture
def encrypted_pdf_factory(tmp_path: Path) -> Callable[..., Path]:
    """Return a factory that writes a tiny password-protected PDF and returns its path."""

    def _make(password: str, name: str = "encrypted.pdf") -> Path:
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.encrypt(user_password=password, owner_password=None)
        path = tmp_path / name
        with path.open("wb") as f:
            writer.write(f)
        return path

    return _make


@pytest.fixture
def docling_document_factory() -> Callable[..., DoclingDocument]:
    """Return a factory that builds a real (offline) DoclingDocument for tests."""

    def _make(
        text: str | None = "Sample text",
        heading: str | None = None,
        list_items: list[str] | None = None,
        with_picture: bool = False,
    ) -> DoclingDocument:
        doc = DoclingDocument(name="test")
        if heading is not None:
            doc.add_text(label=DocItemLabel.SECTION_HEADER, text=heading)
        if text is not None:
            doc.add_text(label=DocItemLabel.TEXT, text=text)
        if list_items:
            group = doc.add_list_group()
            for item in list_items:
                doc.add_list_item(text=item, parent=group)
        if with_picture:
            from PIL import Image

            image = Image.new("RGB", (4, 4), color="red")
            doc.add_picture(image=ImageRef.from_pil(image, dpi=72))
        return doc

    return _make


@pytest.fixture
def conversion_result_factory(
    docling_document_factory: Callable[..., DoclingDocument],
) -> Callable[..., SimpleNamespace]:
    """Return a factory that builds a fake ConversionResult-like object.

    ``document`` is a real DoclingDocument so save_as_markdown runs for real;
    only DocumentConverter.convert() itself is mocked (see mock_docling_convert).
    """

    def _make(
        status: ConversionStatus = ConversionStatus.SUCCESS,
        errors: list[ErrorItem] | None = None,
        **document_kwargs,
    ) -> SimpleNamespace:
        document = docling_document_factory(**document_kwargs)
        return SimpleNamespace(status=status, document=document, errors=errors or [])

    return _make


@pytest.fixture
def error_item_factory() -> Callable[..., ErrorItem]:
    def _make(category: FailureCategory, page_no: int | None = None) -> ErrorItem:
        return ErrorItem(
            component_type=DoclingComponentType.MODEL,
            module_name="test",
            error_message="simulated failure",
            category=category,
            page_no=page_no,
        )

    return _make


@pytest.fixture
def mock_docling_convert(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Patch DocumentConverter.convert so no real (network-dependent) conversion runs."""
    import markwright.core.converter as converter_module

    mock = MagicMock()
    monkeypatch.setattr(converter_module.DocumentConverter, "convert", mock)
    return mock
