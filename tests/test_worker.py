from pathlib import Path

import pytest

from markwright.core.converter import ConversionStage, ConversionWarning
from markwright.core.exceptions import CorruptFileError
from markwright.gui.worker import ConversionJob, DoneEvent, Event, FailedEvent, ProgressEvent

_TIMEOUT_SECONDS = 5


def _run(job: ConversionJob) -> list[Event]:
    """Start the job and collect its events up to (and including) the final one."""
    job.start()
    events: list[Event] = []
    while True:
        event = job.events.get(timeout=_TIMEOUT_SECONDS)
        events.append(event)
        if isinstance(event, DoneEvent | FailedEvent):
            return events


def test_job_forwards_its_inputs_and_reports_progress_then_the_output_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, object] = {}

    def fake_convert(input_path, password=None, on_progress=None):
        received.update(input_path=input_path, password=password)
        on_progress(ConversionStage.STARTED)
        on_progress(ConversionStage.DONE)
        return Path("out.md")

    monkeypatch.setattr("markwright.gui.worker.convert_pdf_to_md", fake_convert)

    events = _run(ConversionJob(Path("in.pdf"), password="secret"))

    assert events == [
        ProgressEvent(ConversionStage.STARTED),
        ProgressEvent(ConversionStage.DONE),
        DoneEvent(Path("out.md")),
    ]
    assert received == {"input_path": Path("in.pdf"), "password": "secret"}


def test_job_forwards_the_warning_of_a_partial_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warning = ConversionWarning(retryable=True, categories=("timeout",), affected_pages=(2,))

    def fake_convert(input_path, password=None, on_progress=None):
        on_progress(ConversionStage.PARTIAL_SUCCESS, warning)
        return Path("out.md")

    monkeypatch.setattr("markwright.gui.worker.convert_pdf_to_md", fake_convert)

    events = _run(ConversionJob(Path("in.pdf")))

    assert events[0] == ProgressEvent(ConversionStage.PARTIAL_SUCCESS, warning)


@pytest.mark.parametrize("error", [CorruptFileError(Path("in.pdf")), RuntimeError("bug")])
def test_job_reports_any_exception_as_a_failure_instead_of_dying_silently(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    def fake_convert(input_path, password=None, on_progress=None):
        raise error

    monkeypatch.setattr("markwright.gui.worker.convert_pdf_to_md", fake_convert)

    events = _run(ConversionJob(Path("in.pdf")))

    assert events == [FailedEvent(error)]
