import runpy
import subprocess
import sys
import tomllib
from importlib import import_module
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from markwright.main import main

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cli_run(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock(return_value=0)
    monkeypatch.setattr("markwright.cli.cli.run", mock)
    return mock


@pytest.fixture
def menu_run(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock(return_value=0)
    monkeypatch.setattr("markwright.cli.menu.run_menu", mock)
    return mock


def test_importing_the_adapters_does_not_load_the_heavy_ml_libraries() -> None:
    code = (
        "import sys, markwright.cli.cli, markwright.cli.menu;"
        "print([m for m in ('docling', 'torch', 'transformers', 'easyocr') if m in sys.modules])"
    )

    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == "[]"


def test_without_arguments_the_interactive_menu_starts(
    cli_run: MagicMock, menu_run: MagicMock
) -> None:
    """The menu is the effortless, no-setup entry point (no desktop GUI is built here —
    see the `gui-desktop` branch)."""
    assert main([]) == 0

    menu_run.assert_called_once_with([])
    cli_run.assert_not_called()


def test_with_a_file_argument_the_cli_runs_and_its_exit_code_is_returned(
    cli_run: MagicMock, menu_run: MagicMock
) -> None:
    cli_run.return_value = 3

    assert main(["report.pdf", "--lang", "es"]) == 3

    cli_run.assert_called_once_with(["report.pdf", "--lang", "es"])
    menu_run.assert_not_called()


def test_menu_as_first_argument_runs_the_interactive_menu(
    cli_run: MagicMock, menu_run: MagicMock
) -> None:
    menu_run.return_value = 7

    assert main(["menu", "--lang", "es"]) == 7

    menu_run.assert_called_once_with(["--lang", "es"])
    cli_run.assert_not_called()


def test_menu_alone_forwards_no_extra_arguments(cli_run: MagicMock, menu_run: MagicMock) -> None:
    main(["menu"])

    menu_run.assert_called_once_with([])


def test_help_alone_goes_to_the_cli_instead_of_the_menu(
    cli_run: MagicMock, menu_run: MagicMock
) -> None:
    main(["--help"])

    cli_run.assert_called_once_with(["--help"])
    menu_run.assert_not_called()


def test_arguments_default_to_sys_argv(monkeypatch: pytest.MonkeyPatch, cli_run: MagicMock) -> None:
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
