import tkinter as tk
from collections.abc import Callable
from dataclasses import replace
from tkinter import ttk

from markwright.gui.settings import Settings
from markwright.i18n import SUPPORTED_LANGUAGES, t


class SettingsDialog(tk.Toplevel):
    """Modal dialog to change language, theme and font size.

    Each choice applies immediately (``on_change``) and is not undone by
    closing the dialog — there is no separate "Apply"/"Cancel" (SET-FR-004).
    """

    def __init__(
        self, parent: tk.Tk, settings: Settings, on_change: Callable[[Settings], None]
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._on_change = on_change
        lang = settings.language

        self.title(t("settings.title", lang))
        self.resizable(False, False)
        self.transient(parent)

        body = ttk.Frame(self, padding=(24, 20))
        body.grid()

        self._language = tk.StringVar(value=settings.language)
        self._theme = tk.StringVar(value=settings.theme)
        self._font_size = tk.StringVar(value=settings.font_size)

        self.language_buttons = self._add_group(
            body,
            0,
            t("settings.language", lang),
            list(SUPPORTED_LANGUAGES.items()),
            self._language,
            self._apply_language,
        )
        self.theme_buttons = self._add_group(
            body,
            1,
            t("settings.theme", lang),
            [("light", t("settings.theme.light", lang)), ("dark", t("settings.theme.dark", lang))],
            self._theme,
            self._apply_theme,
        )
        self.font_size_buttons = self._add_group(
            body,
            2,
            t("settings.font_size", lang),
            [
                ("small", t("settings.font_size.small", lang)),
                ("normal", t("settings.font_size.normal", lang)),
                ("large", t("settings.font_size.large", lang)),
            ],
            self._font_size,
            self._apply_font_size,
        )

        self.grab_set()
        self.focus_set()

    def _add_group(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        options: list[tuple[str, str]],
        variable: tk.StringVar,
        command: Callable[[], None],
    ) -> dict[str, ttk.Radiobutton]:
        top_padding = 0 if row == 0 else 16
        ttk.Label(parent, text=label, style="Subtitle.TLabel").grid(
            row=row * 2, column=0, sticky="w", pady=(top_padding, 4)
        )
        options_row = ttk.Frame(parent)
        options_row.grid(row=row * 2 + 1, column=0, sticky="w")
        buttons: dict[str, ttk.Radiobutton] = {}
        for value, text in options:
            button = ttk.Radiobutton(
                options_row, text=text, value=value, variable=variable, command=command
            )
            button.pack(side="left", padx=(0, 16))
            buttons[value] = button
        return buttons

    def _apply_language(self) -> None:
        self._apply(language=self._language.get())

    def _apply_theme(self) -> None:
        self._apply(theme=self._theme.get())

    def _apply_font_size(self) -> None:
        self._apply(font_size=self._font_size.get())

    def _apply(self, **change: str) -> None:
        self._settings = replace(self._settings, **change)
        self._on_change(self._settings)
