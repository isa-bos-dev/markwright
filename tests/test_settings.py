import json
from pathlib import Path

import pytest

from markwright.gui.settings import (
    DEFAULT_SETTINGS,
    Settings,
    default_settings_path,
    load_settings,
    save_settings,
)


def test_a_missing_file_returns_the_defaults(tmp_path: Path) -> None:
    assert load_settings(tmp_path / "settings.json") == DEFAULT_SETTINGS


def test_invalid_json_returns_the_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("not json", encoding="utf-8")

    assert load_settings(path) == DEFAULT_SETTINGS


def test_a_json_value_that_is_not_an_object_returns_the_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")

    assert load_settings(path) == DEFAULT_SETTINGS


def test_an_unknown_key_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"language": "es", "mystery": "value"}), encoding="utf-8")

    assert load_settings(path) == Settings(language="es")


def test_an_invalid_value_for_one_field_falls_back_while_the_rest_are_applied(
    tmp_path: Path,
) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"language": "es", "theme": "purple"}), encoding="utf-8")

    assert load_settings(path) == Settings(language="es", theme="light")


def test_saving_then_loading_returns_the_same_settings(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    settings = Settings(language="es", theme="dark", font_size="large")

    save_settings(settings, path)

    assert load_settings(path) == settings


def test_saving_creates_the_parent_directory(tmp_path: Path) -> None:
    path = tmp_path / "new_folder" / "settings.json"

    save_settings(Settings(), path)

    assert path.exists()


def test_saving_does_not_leave_a_temporary_file_behind(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"

    save_settings(Settings(), path)

    assert not path.with_suffix(".json.tmp").exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["settings.json"]


def test_a_write_failure_is_silently_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_replace(self: Path, target: Path) -> Path:
        raise OSError("disk full")

    monkeypatch.setattr(Path, "replace", broken_replace)

    save_settings(Settings(), tmp_path / "settings.json")  # must not raise


def test_default_settings_path_is_under_appdata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPDATA", r"C:\Users\someone\AppData\Roaming")

    path = default_settings_path()

    assert path == Path(r"C:\Users\someone\AppData\Roaming") / "Markwright" / "settings.json"


def test_default_settings_path_falls_back_to_home_without_appdata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APPDATA", raising=False)

    path = default_settings_path()

    assert path == Path.home() / "Markwright" / "settings.json"
