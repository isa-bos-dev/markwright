import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

import sv_ttk

# Offset in points applied to every named font's base size (SET-FR-003/004).
FONT_SIZE_OFFSETS: dict[str, int] = {"small": -2, "normal": 0, "large": 2}

# Each named font's pristine size, read the first time it is seen. Re-running
# sv_ttk.set_theme() on the same root does not reset a font once its size has
# been changed, so later calls must scale from this fixed baseline instead of
# the (possibly already-scaled) current size — never a hardcoded literal, so
# this still tracks whatever sizes sv_ttk itself ships.
_base_font_sizes: dict[str, int] = {}


def _scale_named_fonts(root: tk.Tk, offset: int) -> None:
    for name in tkfont.names(root):
        if not (name.startswith("Tk") or name.startswith("SunValley")):
            continue
        font = tkfont.nametofont(name, root)
        base_size = _base_font_sizes.setdefault(name, font.actual("size"))
        font.configure(size=base_size + offset)


def apply_theme(root: tk.Tk, theme: str = "light", font_size: str = "normal") -> None:
    """Apply the Windows 11 (Sun Valley) look, scaled to ``font_size``.

    Fonts are the theme's own named typography scale, so text stays consistent
    with the rest of the theme instead of relying on hard-coded font families.
    Safe to call again on the same ``root`` when the user changes a setting.
    """
    sv_ttk.set_theme(theme, root)
    _scale_named_fonts(root, FONT_SIZE_OFFSETS.get(font_size, 0))

    style = ttk.Style(root)
    style.configure("Title.TLabel", font="SunValleyTitleFont")
    style.configure("Subtitle.TLabel", font="SunValleyBodyLargeFont")
    style.configure("Language.Accent.TButton", font="SunValleyBodyLargeFont", padding=(36, 14))
    # Windows 11 status palette, dark enough for readable contrast on white or black.
    style.configure("Success.TLabel", foreground="#0f7b0f" if theme == "light" else "#6ccb5f")
    style.configure("Warning.TLabel", foreground="#9d5d00" if theme == "light" else "#ffc83d")
    style.configure("Error.TLabel", foreground="#c42b1c" if theme == "light" else "#ff6259")
