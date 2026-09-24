import logging
import os
import queue
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from markwright import APP_NAME
from markwright.core.converter import ConversionStage
from markwright.core.exceptions import InvalidPasswordError
from markwright.gui.assets import load_image
from markwright.gui.worker import ConversionJob, DoneEvent, Event, FailedEvent, ProgressEvent
from markwright.i18n import t
from markwright.i18n.errors import ERROR_MESSAGE_KEYS

_POLL_INTERVAL_MS = 100
_MESSAGE_WIDTH_PX = 480
_CONTENT_COLUMN_MIN_WIDTH_PX = 370
_MASK_CHARACTER = "•"

_log = logging.getLogger(__name__)


class MainScreen(ttk.Frame):
    """Choose a PDF, convert it without freezing the window, and show the result."""

    def __init__(self, parent: tk.Misc, language: str) -> None:
        super().__init__(parent, padding=(40, 32))
        self._language = language
        self._input_path: Path | None = None
        self._output_path: Path | None = None
        self._job: ConversionJob | None = None
        self._warning_text = ""
        self._poll_id: str | None = None
        self._password = tk.StringVar()
        self._build()

    def _t(self, key: str, **values: object) -> str:
        return t(key, self._language, **values)

    def _build(self) -> None:
        header = ttk.Frame(self)
        header.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 24))
        self._logo = load_image("logo-56.png", self)
        ttk.Label(header, image=self._logo).grid(row=0, column=0, rowspan=2)
        ttk.Label(header, text=APP_NAME, style="Title.TLabel").grid(
            row=0, column=1, sticky="sw", padx=(16, 0)
        )
        ttk.Label(header, text=self._t("main.subtitle"), style="Subtitle.TLabel").grid(
            row=1, column=1, sticky="nw", padx=(16, 0)
        )

        self.choose_button = ttk.Button(
            self, text=self._t("main.choose_file"), command=self._choose_file
        )
        self.choose_button.grid(row=1, column=0, sticky="w")
        self.file_label = ttk.Label(self, text=self._t("main.no_file"))
        self.file_label.grid(row=1, column=1, sticky="w", padx=(16, 0))

        self.password_label = ttk.Label(self, text=self._t("main.password"))
        self.password_entry = ttk.Entry(self, textvariable=self._password, show=_MASK_CHARACTER)
        self.password_entry.bind("<Return>", lambda _event: self._start_conversion())
        self.password_label.grid(row=2, column=0, sticky="w", pady=(16, 0))
        self.password_entry.grid(row=2, column=1, sticky="ew", padx=(16, 0), pady=(16, 0))
        self._set_password_visible(False)

        self.convert_button = ttk.Button(
            self,
            text=self._t("main.convert"),
            style="Accent.TButton",
            command=self._start_conversion,
        )
        self.convert_button.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(24, 0))
        self.convert_button.state(["disabled"])

        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(24, 0))
        self.progress.grid_remove()

        self.status_label = ttk.Label(self, wraplength=_MESSAGE_WIDTH_PX, justify="left")
        self.status_label.grid(row=5, column=0, columnspan=2, sticky="w", pady=(16, 0))

        self.open_folder_button = ttk.Button(
            self, text=self._t("main.open_folder"), command=self._open_folder
        )
        self.open_folder_button.grid(row=6, column=0, columnspan=2, sticky="w", pady=(12, 0))
        self.open_folder_button.grid_remove()

        # A stable minimum width keeps the window from jumping between states.
        self.columnconfigure(1, weight=1, minsize=_CONTENT_COLUMN_MIN_WIDTH_PX)

    def _set_password_visible(self, visible: bool) -> None:
        for widget in (self.password_label, self.password_entry):
            if visible:
                widget.grid()
            else:
                widget.grid_remove()

    def _choose_file(self) -> None:
        filename = filedialog.askopenfilename(
            title=self._t("main.file_dialog_title"),
            filetypes=[(self._t("main.file_type_pdf"), "*.pdf")],
        )
        if not filename:
            return
        self._input_path = Path(filename)
        self.file_label.configure(text=self._input_path.name)
        self.convert_button.state(["!disabled"])
        self._password.set("")
        self._set_password_visible(False)
        self._show_status("")
        self.open_folder_button.grid_remove()

    def _start_conversion(self) -> None:
        if self._input_path is None or self._job is not None:
            return
        self._show_status("")
        self._warning_text = ""
        self.open_folder_button.grid_remove()
        self._set_busy(True)
        self._job = ConversionJob(self._input_path, password=self._password.get() or None)
        self._job.start()
        self._poll_id = self.after(_POLL_INTERVAL_MS, self._poll)

    def _set_busy(self, busy: bool) -> None:
        state = ["disabled"] if busy else ["!disabled"]
        for widget in (self.choose_button, self.convert_button, self.password_entry):
            widget.state(state)
        if busy:
            self.progress.grid()
            self.progress.start()
        else:
            self.progress.stop()
            self.progress.grid_remove()

    def _poll(self) -> None:
        self._poll_id = None
        if self._job is None:
            return
        finished = False
        while not finished:
            try:
                event = self._job.events.get_nowait()
            except queue.Empty:
                break
            finished = self._handle(event)
        if finished:
            self._job = None
        else:
            self._poll_id = self.after(_POLL_INTERVAL_MS, self._poll)

    def _handle(self, event: Event) -> bool:
        """Apply one worker event to the screen; True once the job has ended."""
        if isinstance(event, ProgressEvent):
            self._on_progress(event)
            return False
        self._set_busy(False)
        if isinstance(event, DoneEvent):
            self._on_done(event.output_path)
        elif isinstance(event, FailedEvent):
            self._on_failed(event.error)
        return True

    def _on_progress(self, event: ProgressEvent) -> None:
        if event.stage == ConversionStage.PARTIAL_SUCCESS:
            retryable = event.warning is not None and event.warning.retryable
            key = f"progress.partial_success.{'retryable' if retryable else 'not_retryable'}"
            self._warning_text = self._t(key)
        else:
            self._show_status(self._t(f"progress.{event.stage.value}"))

    def _on_done(self, output_path: Path) -> None:
        self._output_path = output_path
        saved = self._t("main.saved_to", path=output_path)
        if self._warning_text:
            self._show_status(f"{self._warning_text}\n{saved}", "Warning.TLabel")
        else:
            self._show_status(f"✓ {saved}", "Success.TLabel")
        self.open_folder_button.grid()

    def _on_failed(self, error: Exception) -> None:
        key = ERROR_MESSAGE_KEYS.get(type(error))
        if key is None:
            _log.error("Unexpected error during conversion", exc_info=error)
            self._show_status(self._t("error.unexpected_gui"), "Error.TLabel")
            return
        self._show_status(self._t(key, path=getattr(error, "path", "")), "Error.TLabel")
        if isinstance(error, InvalidPasswordError):
            self._set_password_visible(True)
            self.password_entry.focus_set()

    def _show_status(self, text: str, style: str = "TLabel") -> None:
        self.status_label.configure(text=text, style=style)

    def _open_folder(self) -> None:
        if self._output_path is not None:
            _open_in_file_manager(self._output_path.parent)

    def destroy(self) -> None:
        if self._poll_id is not None:
            self.after_cancel(self._poll_id)
            self._poll_id = None
        super().destroy()


def _open_in_file_manager(folder: Path) -> None:
    if sys.platform == "win32":
        os.startfile(folder)
    elif sys.platform == "darwin":
        subprocess.run(["open", str(folder)], check=False)
    else:
        subprocess.run(["xdg-open", str(folder)], check=False)
