import tkinter as tk
from tkinter import ttk


class Tooltip:
    """A small borderless popup with ``text``, shown while the mouse hovers ``widget``.

    ``text`` is a public attribute so callers can update it (e.g. after the
    user changes the interface language) without recreating the tooltip.
    """

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.text = text
        self._widget = widget
        self._popup: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event: object = None) -> None:
        if self._popup is not None:
            return
        x = self._widget.winfo_rootx()
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
        self._popup = tk.Toplevel(self._widget)
        self._popup.wm_overrideredirect(True)
        self._popup.wm_geometry(f"+{x}+{y}")
        ttk.Label(self._popup, text=self.text, padding=(6, 3), relief="solid", borderwidth=1).pack()

    def _hide(self, _event: object = None) -> None:
        if self._popup is not None:
            self._popup.destroy()
            self._popup = None
