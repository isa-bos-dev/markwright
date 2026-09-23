import tkinter as tk

from markwright import APP_NAME
from markwright.gui.language_screen import LanguageScreen
from markwright.gui.theme import apply_theme


class App(tk.Tk):
    """The single application window; screens are swapped inside it."""

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.resizable(False, False)
        self.selected_language: str | None = None
        apply_theme(self)

        self.screen = LanguageScreen(self, on_selected=self._on_language_selected)
        self.screen.pack()
        self._center_on_screen()

    def _on_language_selected(self, language: str) -> None:
        self.selected_language = language
        self.destroy()

    def _center_on_screen(self) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_reqwidth()) // 2
        y = (self.winfo_screenheight() - self.winfo_reqheight()) // 3
        self.geometry(f"+{x}+{y}")


def run() -> str | None:
    """Show the language screen and return the chosen code, or None if closed."""
    app = App()
    app.mainloop()
    return app.selected_language
