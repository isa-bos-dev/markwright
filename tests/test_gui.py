import threading
import time
import tkinter as tk
from collections.abc import Callable, Iterator
from pathlib import Path
from tkinter import filedialog

import pytest

from markwright.core.converter import ConversionStage, ConversionWarning
from markwright.core.exceptions import InvalidPasswordError
from markwright.gui.assets import load_image
from markwright.gui.gui import App
from markwright.gui.language_screen import LanguageScreen, build_language_prompt
from markwright.gui.main_screen import MainScreen
from markwright.gui.theme import apply_theme
from markwright.i18n import SUPPORTED_LANGUAGES, t

_WAIT_TIMEOUT_SECONDS = 5


@pytest.fixture(scope="session")
def tk_root() -> Iterator[tk.Tk]:
    """One hidden Tk root shared by the whole session (each Tk start-up is costly).

    The GUI tests are skipped when the machine has no display.
    """
    try:
        root = tk.Tk()
    except tk.TclError as error:
        if "display" not in str(error):
            raise
        pytest.skip(f"no display available for Tk: {error}")
    root.withdraw()
    apply_theme(root)
    yield root
    root.destroy()


@pytest.fixture
def selections(tk_root: tk.Tk) -> Iterator[tuple[LanguageScreen, list[str]]]:
    selected: list[str] = []
    screen = LanguageScreen(tk_root, on_selected=selected.append)
    yield screen, selected
    screen.destroy()


@pytest.fixture
def main_screen(tk_root: tk.Tk) -> Iterator[MainScreen]:
    screen = MainScreen(tk_root, "en")
    yield screen
    screen.destroy()


def _pump(root: tk.Tk, condition: Callable[[], bool]) -> None:
    """Process Tk events until ``condition()`` holds (the GUI polls its worker via after())."""
    deadline = time.monotonic() + _WAIT_TIMEOUT_SECONDS
    while not condition():
        if time.monotonic() > deadline:
            pytest.fail("timed out waiting for the GUI")
        root.update()
        time.sleep(0.01)


def _is_shown(widget: tk.Widget) -> bool:
    return bool(widget.grid_info())


def _choose_pdf(screen: MainScreen, monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **_: str(path))
    screen.choose_button.invoke()


def _fake_conversion(monkeypatch: pytest.MonkeyPatch, fake: Callable[..., Path]) -> None:
    monkeypatch.setattr("markwright.gui.worker.convert_pdf_to_md", fake)


def test_packaged_images_load_at_their_declared_size(tk_root: tk.Tk) -> None:
    image = load_image("logo-96.png", tk_root)

    assert (image.width(), image.height()) == (96, 96)


# --- Language screen ---


def test_prompt_contains_the_prompt_of_every_supported_language() -> None:
    assert build_language_prompt() == "Select your language / Selecciona tu idioma"


def test_one_button_per_supported_language_with_native_names_in_order(
    selections: tuple[LanguageScreen, list[str]],
) -> None:
    screen, _ = selections

    assert list(screen.buttons) == list(SUPPORTED_LANGUAGES)
    assert [button.cget("text") for button in screen.buttons.values()] == list(
        SUPPORTED_LANGUAGES.values()
    )


def test_clicking_a_language_button_reports_its_code(
    selections: tuple[LanguageScreen, list[str]],
) -> None:
    screen, selected = selections

    screen.buttons["es"].invoke()
    screen.buttons["en"].invoke()

    assert selected == ["es", "en"]


@pytest.mark.usefixtures("tk_root")
def test_app_starts_on_the_language_screen_then_moves_to_the_main_screen() -> None:
    app = App()
    app.withdraw()
    try:
        assert len(app.winfo_children()) == 1
        assert isinstance(app.screen, LanguageScreen)

        app.screen.buttons["es"].invoke()

        assert isinstance(app.screen, MainScreen)
        assert app.screen.convert_button.cget("text") == t("main.convert", "es")
    finally:
        app.destroy()


# --- Main screen ---


def test_choosing_a_pdf_and_converting_shows_where_the_result_was_saved(
    main_screen: MainScreen,
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "report.md"
    _fake_conversion(monkeypatch, lambda input_path, password=None, on_progress=None: output)
    assert main_screen.convert_button.instate(["disabled"])

    _choose_pdf(main_screen, monkeypatch, tmp_path / "report.pdf")
    assert main_screen.file_label.cget("text") == "report.pdf"
    assert main_screen.convert_button.instate(["!disabled"])

    main_screen.convert_button.invoke()
    _pump(tk_root, lambda: _is_shown(main_screen.open_folder_button))

    assert t("main.saved_to", "en", path=output) in main_screen.status_label.cget("text")


def test_a_protected_pdf_asks_for_the_password_and_retries_with_it(
    main_screen: MainScreen,
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[str | None] = []

    def fake_convert(input_path, password=None, on_progress=None):
        calls.append(password)
        if password != "right":
            raise InvalidPasswordError(input_path)
        return tmp_path / "report.md"

    _fake_conversion(monkeypatch, fake_convert)
    assert not _is_shown(main_screen.password_entry)
    assert main_screen.password_entry.cget("show") == "•"

    pdf = tmp_path / "report.pdf"
    _choose_pdf(main_screen, monkeypatch, pdf)
    main_screen.convert_button.invoke()
    _pump(tk_root, lambda: _is_shown(main_screen.password_entry))
    assert t("error.invalid_password", "en", path=pdf) in main_screen.status_label.cget("text")

    main_screen.password_entry.insert(0, "right")
    main_screen.convert_button.invoke()
    _pump(tk_root, lambda: _is_shown(main_screen.open_folder_button))

    assert calls == [None, "right"]


def test_a_partial_conversion_shows_the_warning_and_the_saved_file(
    main_screen: MainScreen,
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "report.md"
    warning = ConversionWarning(retryable=True, categories=("timeout",), affected_pages=(2,))

    def fake_convert(input_path, password=None, on_progress=None):
        on_progress(ConversionStage.PARTIAL_SUCCESS, warning)
        return output

    _fake_conversion(monkeypatch, fake_convert)
    _choose_pdf(main_screen, monkeypatch, tmp_path / "report.pdf")

    main_screen.convert_button.invoke()
    _pump(tk_root, lambda: _is_shown(main_screen.open_folder_button))

    text = main_screen.status_label.cget("text")
    assert t("progress.partial_success.retryable", "en") in text
    assert t("main.saved_to", "en", path=output) in text


def test_controls_are_locked_while_converting_and_unlocked_afterwards(
    main_screen: MainScreen,
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    release = threading.Event()

    def slow_convert(input_path, password=None, on_progress=None):
        release.wait(timeout=_WAIT_TIMEOUT_SECONDS)
        return tmp_path / "report.md"

    _fake_conversion(monkeypatch, slow_convert)
    _choose_pdf(main_screen, monkeypatch, tmp_path / "report.pdf")

    main_screen.convert_button.invoke()

    assert main_screen.convert_button.instate(["disabled"])
    assert main_screen.choose_button.instate(["disabled"])
    assert _is_shown(main_screen.progress)

    release.set()
    _pump(tk_root, lambda: _is_shown(main_screen.open_folder_button))

    assert main_screen.convert_button.instate(["!disabled"])
    assert not _is_shown(main_screen.progress)
