from importlib.metadata import PackageNotFoundError, metadata, version
from pathlib import Path

import pytest

from markwright import get_version

_ROOT = Path(__file__).resolve().parents[1]


def test_get_version_matches_the_installed_package_metadata() -> None:
    assert get_version() == version("markwright")


def test_get_version_falls_back_when_metadata_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing(_name: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr("markwright.version", missing)

    assert get_version() == "0.0.0+unknown"


def test_the_package_declares_its_license_and_author() -> None:
    package = metadata("markwright")

    assert package["License-Expression"] == "Apache-2.0"
    assert package["Author"] == "IsaBosDev"


def test_the_published_metadata_contains_no_personal_email() -> None:
    package = metadata("markwright")

    assert package.get("Author-email") is None
    assert "@" not in (package.get("Author") or "")


def test_the_repository_ships_the_license_and_notice_files() -> None:
    assert (_ROOT / "LICENSE").read_text(encoding="utf-8").lstrip().startswith("Apache License")
    assert "IsaBosDev" in (_ROOT / "NOTICE").read_text(encoding="utf-8")
