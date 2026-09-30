import tkinter as tk

from markwright import APP_NAME
from markwright.gui.assets import load_image
from markwright.gui.main_screen import MainScreen
from markwright.gui.settings import Settings, load_settings, save_settings
from markwright.gui.settings_dialog import SettingsDialog
from markwright.gui.theme import apply_theme


class App(tk.Tk):
    """The single application window, started directly on the main screen."""

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.resizable(False, False)
        self._window_icons = [load_image(f"icon-{side}.png", self) for side in (32, 64, 256)]
        self.iconphoto(True, *self._window_icons)

        self._settings = load_settings()
        apply_theme(self, theme=self._settings.theme, font_size=self._settings.font_size)

        self.screen = MainScreen(
            self, self._settings.language, on_open_settings=self._open_settings
        )
        self.screen.pack()
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_reqwidth()) // 2
        y = (self.winfo_screenheight() - self.winfo_reqheight()) // 3
        self.geometry(f"+{x}+{y}")

    def _open_settings(self) -> None:
        SettingsDialog(self, self._settings, on_change=self._apply_settings)

    def _apply_settings(self, settings: Settings) -> None:
        self._settings = settings
        apply_theme(self, theme=settings.theme, font_size=settings.font_size)
        self.screen.refresh_language(settings.language)
        save_settings(settings)


def run() -> None:
    App().mainloop()
