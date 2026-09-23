import sys
from pathlib import Path

import pytest

from markwright.core.models import MODELS_DIR_ENV_VAR, find_models_dir


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Start every test from an empty working directory with no override set."""
    monkeypatch.delenv(MODELS_DIR_ENV_VAR, raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_the_environment_variable_takes_priority(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configured = tmp_path / "custom-models"
    configured.mkdir()
    (tmp_path / "models").mkdir()
    monkeypatch.setenv(MODELS_DIR_ENV_VAR, str(configured))

    assert find_models_dir() == configured


def test_a_frozen_application_uses_the_models_folder_next_to_its_executable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app_dir = tmp_path / "app"
    (app_dir / "models").mkdir(parents=True)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(app_dir / "markwright.exe"))

    assert find_models_dir() == app_dir / "models"


def test_it_falls_back_to_the_models_folder_of_the_working_directory(tmp_path: Path) -> None:
    (tmp_path / "models").mkdir()

    assert find_models_dir() == tmp_path / "models"


def test_it_returns_none_when_there_is_no_models_folder() -> None:
    assert find_models_dir() is None


def test_a_configured_path_that_is_not_a_directory_is_ignored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    not_a_directory = tmp_path / "models.txt"
    not_a_directory.write_text("not a folder")
    (tmp_path / "models").mkdir()
    monkeypatch.setenv(MODELS_DIR_ENV_VAR, str(not_a_directory))

    assert find_models_dir() == tmp_path / "models"
