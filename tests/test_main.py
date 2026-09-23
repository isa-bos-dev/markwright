import runpy
import subprocess
import sys
import tkinter as tk
import tomllib
from importlib import import_module
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from markwright.main import EXIT_GUI_UNAVAILABLE, main

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cli_run(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock(return_value=0)
    monkeypatch.setattr("markwright.cli.cli.run", mock)
    return mock


@pytest.fixture
def gui_run(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    monkeypatch.setattr("markwright.gui.gui.run", mock)
    return mock


def test_importing_the_adapters_does_not_load_the_heavy_ml_libraries() -> None:
    code = (
        "import sys, markwright.cli.cli, markwright.gui.gui;"
        "print([m for m in ('docling', 'torch', 'transformers', 'easyocr') if m in sys.modules])"
    )

    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == "[]"


def test_without_arguments_the_gui_starts(gui_run: MagicMock, cli_run: MagicMock) -> None:
    assert main([]) == 0

    gui_run.assert_called_once_with()
    cli_run.assert_not_called()


def test_with_arguments_the_cli_runs_and_its_exit_code_is_returned(
    gui_run: MagicMock, cli_run: MagicMock
) -> None:
    cli_run.return_value = 3

    assert main(["report.pdf", "--lang", "es"]) == 3

    cli_run.assert_called_once_with(["report.pdf", "--lang", "es"])
    gui_run.assert_not_called()


def test_help_alone_goes_to_the_cli_instead_of_opening_the_gui(
    gui_run: MagicMock, cli_run: MagicMock
) -> None:
    main(["--help"])

    cli_run.assert_called_once_with(["--help"])
    gui_run.assert_not_called()


def test_arguments_default_to_sys_argv(
    monkeypatch: pytest.MonkeyPatch, cli_run: MagicMock
) -> None:
    monkeypatch.setattr(sys, "argv", ["markwright", "report.pdf"])

    main()

    cli_run.assert_called_once_with(["report.pdf"])


def test_running_the_package_with_dash_m_exits_with_the_returned_code(
    monkeypatch: pytest.MonkeyPatch, cli_run: MagicMock
) -> None:
    cli_run.return_value = 4
    monkeypatch.setattr(sys, "argv", ["markwright", "report.pdf"])

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("markwright", run_name="__main__")

    assert exc_info.value.code == 4


def test_the_markwright_command_is_registered_and_resolves_to_main() -> None:
    pyproject = tomllib.loads((_PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    module_name, function_name = pyproject["project"]["scripts"]["markwright"].split(":")

    assert getattr(import_module(module_name), function_name) is main


def test_a_gui_that_cannot_start_reports_it_clearly_and_points_to_the_cli(
    gui_run: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    gui_run.side_effect = tk.TclError("no display name and no $DISPLAY environment variable")

    assert main([]) == EXIT_GUI_UNAVAILABLE

    error_output = capsys.readouterr().err
    assert "no display name" in error_output
    assert "markwright <file.pdf>" in error_output
    assert "Traceback" not in error_output


def test_a_missing_tkinter_is_reported_the_same_way(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setitem(sys.modules, "markwright.gui.gui", None)

    assert main([]) == EXIT_GUI_UNAVAILABLE

    assert "markwright <file.pdf>" in capsys.readouterr().err
