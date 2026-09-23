import queue
import threading
from dataclasses import dataclass
from pathlib import Path

from markwright.core.converter import ConversionStage, ConversionWarning, convert_pdf_to_md


@dataclass(frozen=True)
class ProgressEvent:
    stage: ConversionStage
    warning: ConversionWarning | None = None


@dataclass(frozen=True)
class DoneEvent:
    output_path: Path


@dataclass(frozen=True)
class FailedEvent:
    error: Exception


Event = ProgressEvent | DoneEvent | FailedEvent


class ConversionJob:
    """Runs one conversion in a background thread and reports through a queue.

    The thread never touches a widget: the GUI reads ``events`` from its own
    thread, so the window stays responsive while docling works.
    """

    def __init__(self, input_path: Path, password: str | None = None) -> None:
        self.events: queue.Queue[Event] = queue.Queue()
        self._input_path = input_path
        self._password = password
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        try:
            output_path = convert_pdf_to_md(
                self._input_path,
                password=self._password,
                on_progress=lambda stage, warning=None: self.events.put(
                    ProgressEvent(stage, warning)
                ),
            )
        except Exception as error:  # noqa: BLE001 - anything that fails must reach the UI
            self.events.put(FailedEvent(error))
        else:
            self.events.put(DoneEvent(output_path))
