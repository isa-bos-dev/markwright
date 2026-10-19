from collections.abc import Callable
from io import BytesIO
from pathlib import Path

import pytest
from docling.datamodel.base_models import DocumentStream
from docling_core.types.doc import BoundingBox
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, StreamObject

from markwright.core.exceptions import InvalidPasswordError
from markwright.core.pdf_source import count_pages, open_region_reader, prepare_docling_source

# --- Success cases ---


def test_unencrypted_pdf_without_password_returns_the_original_path(
    plain_pdf_factory: Callable[..., Path],
) -> None:
    path = plain_pdf_factory()

    result = prepare_docling_source(path)

    assert result == path


def test_unencrypted_pdf_with_password_ignores_the_password(
    plain_pdf_factory: Callable[..., Path],
) -> None:
    path = plain_pdf_factory()

    result = prepare_docling_source(path, password="irrelevant")

    assert result == path


def test_encrypted_pdf_with_correct_password_returns_a_document_stream(
    encrypted_pdf_factory: Callable[..., Path],
) -> None:
    path = encrypted_pdf_factory(password="right-pw")

    result = prepare_docling_source(path, password="right-pw")

    assert isinstance(result, DocumentStream)
    decrypted_reader = PdfReader(result.stream)
    assert not decrypted_reader.is_encrypted
    assert len(decrypted_reader.pages) == 1


def test_document_stream_keeps_the_original_file_name(
    encrypted_pdf_factory: Callable[..., Path],
) -> None:
    path = encrypted_pdf_factory(password="right-pw", name="secret_report.pdf")

    result = prepare_docling_source(path, password="right-pw")

    assert result.name == "secret_report.pdf"


# --- Error cases ---


def test_encrypted_pdf_without_password_raises(
    encrypted_pdf_factory: Callable[..., Path],
) -> None:
    path = encrypted_pdf_factory(password="right-pw")

    with pytest.raises(InvalidPasswordError):
        prepare_docling_source(path)


def test_encrypted_pdf_with_empty_password_raises(
    encrypted_pdf_factory: Callable[..., Path],
) -> None:
    path = encrypted_pdf_factory(password="right-pw")

    with pytest.raises(InvalidPasswordError):
        prepare_docling_source(path, password="")


def test_encrypted_pdf_with_wrong_password_raises(
    encrypted_pdf_factory: Callable[..., Path],
) -> None:
    path = encrypted_pdf_factory(password="right-pw")

    with pytest.raises(InvalidPasswordError):
        prepare_docling_source(path, password="wrong-pw")


def test_invalid_password_error_never_exposes_the_password(
    encrypted_pdf_factory: Callable[..., Path],
) -> None:
    path = encrypted_pdf_factory(password="super-secret")

    try:
        prepare_docling_source(path, password="also-a-secret-guess")
        pytest.fail("expected InvalidPasswordError to be raised")
    except InvalidPasswordError as exc:
        assert "super-secret" not in str(exc)
        assert "also-a-secret-guess" not in str(exc)


def test_successful_decryption_does_not_write_any_file_to_disk(
    encrypted_pdf_factory: Callable[..., Path], tmp_path: Path
) -> None:
    path = encrypted_pdf_factory(password="right-pw")
    before = set(tmp_path.rglob("*"))

    prepare_docling_source(path, password="right-pw")

    after = set(tmp_path.rglob("*"))
    assert before == after


def test_count_pages_rewinds_a_decrypted_stream(
    encrypted_pdf_factory: Callable[..., Path],
) -> None:
    source = prepare_docling_source(encrypted_pdf_factory(password="right-pw"), "right-pw")

    assert count_pages(source) == 1
    assert source.stream.tell() == 0


def _pdf_with_two_text_lines(path: Path) -> Path:
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=100)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    content = StreamObject()
    content.set_data(b"BT /F1 12 Tf 10 60 Td (int x;) Tj 0 -20 Td (return x;) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(content)
    with path.open("wb") as f:
        writer.write(f)
    return path


def test_region_reader_returns_the_text_layer_with_its_line_breaks(tmp_path: Path) -> None:
    path = _pdf_with_two_text_lines(tmp_path / "code.pdf")

    with open_region_reader(path) as read_region:
        text = read_region(1, BoundingBox(l=0, t=100, r=200, b=0))

    assert text.splitlines() == ["int x;", "return x;"]


def test_region_reader_also_reads_a_decrypted_in_memory_stream(tmp_path: Path) -> None:
    path = _pdf_with_two_text_lines(tmp_path / "code.pdf")
    stream = DocumentStream(name="code.pdf", stream=BytesIO(path.read_bytes()))

    with open_region_reader(stream) as read_region:
        text = read_region(1, BoundingBox(l=0, t=100, r=200, b=0))

    assert "return x;" in text
