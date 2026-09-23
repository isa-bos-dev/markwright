import tkinter as tk
from collections.abc import Callable
from functools import partial
from tkinter import ttk

from markwright import APP_NAME
from markwright.gui.assets import load_image
from markwright.i18n import SUPPORTED_LANGUAGES, t

_PROMPT_SEPARATOR = " / "


def build_language_prompt() -> str:
    """The prompt in every supported language, since none has been chosen yet."""
    return _PROMPT_SEPARATOR.join(
        t("language_selector.prompt", code) for code in SUPPORTED_LANGUAGES
    )


class LanguageScreen(ttk.Frame):
    """First screen: one button per supported language."""

    def __init__(self, parent: tk.Misc, on_selected: Callable[[str], None]) -> None:
        super().__init__(parent, padding=(48, 40))
        columns = len(SUPPORTED_LANGUAGES)

        self._logo = load_image("logo-96.png", self)
        ttk.Label(self, image=self._logo).grid(row=0, column=0, columnspan=columns, pady=(0, 16))
        ttk.Label(self, text=APP_NAME, style="Title.TLabel").grid(
            row=1, column=0, columnspan=columns
        )
        ttk.Label(
            self, text=build_language_prompt(), style="Subtitle.TLabel", justify="center"
        ).grid(row=2, column=0, columnspan=columns, pady=(8, 32))

        self.buttons: dict[str, ttk.Button] = {}
        for column, (code, name) in enumerate(SUPPORTED_LANGUAGES.items()):
            button = ttk.Button(
                self,
                text=name,
                style="Language.Accent.TButton",
                command=partial(on_selected, code),
            )
            button.grid(row=3, column=column, padx=8, sticky="ew")
            self.buttons[code] = button
