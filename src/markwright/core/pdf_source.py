from io import BytesIO
from pathlib import Path

from docling.datamodel.base_models import DocumentStream
from pypdf import PdfReader, PdfWriter
from pypdf.errors import WrongPasswordError

from markwright.core.exceptions import InvalidPasswordError


def prepare_docling_source(input_path: Path, password: str | None = None) -> Path | DocumentStream:
    """Return a source docling can convert directly.

    Unencrypted PDFs pass through untouched as a ``Path``. Encrypted PDFs are
    decrypted entirely in memory and returned as a ``DocumentStream`` — the
    decrypted content is never written to disk.
    """
    reader = PdfReader(input_path)
    if not reader.is_encrypted:
        return input_path

    if not password:
        raise InvalidPasswordError(input_path)

    try:
        reader = PdfReader(input_path, password=password)
    except WrongPasswordError:
        raise InvalidPasswordError(input_path) from None

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    buffer = BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return DocumentStream(name=input_path.name, stream=buffer)
