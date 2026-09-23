from importlib.metadata import metadata
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


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
