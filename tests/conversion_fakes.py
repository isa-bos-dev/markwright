"""Stand-ins for ``convert_pdf_to_md`` shared by the GUI and worker tests.

Each one has the real function's signature, so it can replace it directly.
"""

import threading
from collections.abc import Callable
from pathlib import Path

import pytest

FakeConversion = Callable[..., Path]

_RELEASE_TIMEOUT_SECONDS = 5


def install(monkeypatch: pytest.MonkeyPatch, fake: FakeConversion) -> None:
    """Make the GUI worker call ``fake`` instead of the real conversion."""
    monkeypatch.setattr("markwright.gui.worker.convert_pdf_to_md", fake)


def returning(output: Path) -> FakeConversion:
    def convert(input_path, password=None, on_progress=None):
        return output

    return convert


def raising(make_error: Callable[[Path], Exception]) -> FakeConversion:
    """A conversion that fails with the error ``make_error`` builds from the input path."""

    def convert(input_path, password=None, on_progress=None):
        raise make_error(input_path)

    return convert


def blocked_until(
    release: threading.Event, output: Path, calls: list[int] | None = None
) -> FakeConversion:
    """A conversion that waits for ``release`` (recording each start in ``calls``)."""

    def convert(input_path, password=None, on_progress=None):
        if calls is not None:
            calls.append(1)
        release.wait(timeout=_RELEASE_TIMEOUT_SECONDS)
        return output

    return convert
