import tkinter as tk
from collections.abc import Iterator

import pytest

from markwright.gui.gui import App
from markwright.gui.language_screen import LanguageScreen, build_language_prompt
from markwright.gui.theme import apply_theme
from markwright.i18n import SUPPORTED_LANGUAGES


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
def test_the_language_screen_is_the_only_thing_shown_on_startup() -> None:
    app = App()
    app.withdraw()
    try:
        children = app.winfo_children()

        assert len(children) == 1
        assert isinstance(children[0], LanguageScreen)
    finally:
        app.destroy()
