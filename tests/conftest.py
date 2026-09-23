from collections.abc import Callable
from pathlib import Path

import pytest
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
