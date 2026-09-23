from collections.abc import Callable
from pathlib import Path

import pytest
from docling.datamodel.base_models import DocumentStream
from pypdf import PdfReader

from markwright.core.exceptions import InvalidPasswordError
from markwright.core.pdf_source import prepare_docling_source

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
