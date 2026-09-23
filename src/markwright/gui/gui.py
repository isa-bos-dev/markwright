import tkinter as tk
from tkinter import ttk

from markwright import APP_NAME
from markwright.gui.assets import load_image
from markwright.gui.language_screen import LanguageScreen
from markwright.gui.main_screen import MainScreen
from markwright.gui.theme import apply_theme


class App(tk.Tk):
    """The single application window; screens are swapped inside it."""

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.resizable(False, False)
        self._window_icons = [load_image(f"icon-{side}.png", self) for side in (32, 64, 256)]
        self.iconphoto(True, *self._window_icons)
        apply_theme(self)

        self.screen: ttk.Frame = LanguageScreen(self, on_selected=self._on_language_selected)
        self._show(self.screen)

    def _on_language_selected(self, language: str) -> None:
        self.screen.destroy()
        self.screen = MainScreen(self, language)
        self._show(self.screen)

    def _show(self, screen: ttk.Frame) -> None:
        screen.pack()
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_reqwidth()) // 2
        y = (self.winfo_screenheight() - self.winfo_reqheight()) // 3
        self.geometry(f"+{x}+{y}")


def run() -> None:
    App().mainloop()
