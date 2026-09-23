from pathlib import Path

import pytest
from PIL import Image

_ROOT = Path(__file__).resolve().parents[1]
_PACKAGE_ASSETS = _ROOT / "src" / "markwright" / "assets"
_README_LOGO = _ROOT / "assets" / "logo-512.png"
_WINDOWS_ICON_SIZES = {(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)}


@pytest.mark.parametrize(
    ("path", "side"),
    [
        (_PACKAGE_ASSETS / "logo-56.png", 56),
        (_PACKAGE_ASSETS / "logo-96.png", 96),
        (_PACKAGE_ASSETS / "icon-32.png", 32),
        (_PACKAGE_ASSETS / "icon-64.png", 64),
        (_PACKAGE_ASSETS / "icon-256.png", 256),
        (_README_LOGO, 512),
    ],
    ids=lambda value: value.name if isinstance(value, Path) else str(value),
)
def test_generated_logo_images_are_square_with_transparency(path: Path, side: int) -> None:
    with Image.open(path) as image:
        assert image.size == (side, side)
        assert image.mode == "RGBA"
        assert image.getchannel("A").getextrema()[0] == 0


def test_the_windows_icon_contains_every_standard_resolution() -> None:
    with Image.open(_PACKAGE_ASSETS / "icon.ico") as icon:
        assert icon.info["sizes"] == _WINDOWS_ICON_SIZES
