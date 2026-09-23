import tkinter as tk
from tkinter import ttk

import sv_ttk


def apply_theme(root: tk.Tk) -> None:
    """Apply the Windows 11 (Sun Valley) look and the app's shared widget styles.

    Fonts are the theme's own named typography scale, so text stays consistent
    with the rest of the theme instead of relying on hard-coded font families.
    """
    sv_ttk.set_theme("light", root)
    style = ttk.Style(root)
    style.configure("Title.TLabel", font="SunValleyTitleFont")
    style.configure("Subtitle.TLabel", font="SunValleyBodyLargeFont")
    style.configure("Language.Accent.TButton", font="SunValleyBodyLargeFont", padding=(36, 14))
    # Windows 11 status palette, dark enough for readable contrast on white.
    style.configure("Success.TLabel", foreground="#0f7b0f")
    style.configure("Warning.TLabel", foreground="#9d5d00")
    style.configure("Error.TLabel", foreground="#c42b1c")
