import tkinter as tk
from importlib.resources import files

_ASSETS = files("markwright") / "assets"


def load_image(name: str, master: tk.Misc) -> tk.PhotoImage:
    """Load a packaged PNG. Keep a reference to it, or Tk discards the image."""
    return tk.PhotoImage(master=master, file=str(_ASSETS / name))
