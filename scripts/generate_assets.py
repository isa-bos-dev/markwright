"""Regenerate every derived brand asset from ``assets/logo.png``.

Run from the project root:  uv run python scripts/generate_assets.py
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "assets" / "logo.png"
README_LOGO = ROOT / "assets" / "logo-512.png"
PACKAGE_ASSETS = ROOT / "src" / "markwright" / "assets"

ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
WINDOW_ICON_SIZES = (32, 64, 256)
UI_LOGO_SIZES = (56, 96)
README_LOGO_SIZE = 512


def tight_square(image: Image.Image) -> Image.Image:
    """Crop the transparent margin, then centre the content on a square canvas."""
    box = image.getchannel("A").point(lambda value: 255 if value > 10 else 0).getbbox()
    cropped = image.crop(box)
    side = max(cropped.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(cropped, ((side - cropped.width) // 2, (side - cropped.height) // 2))
    return canvas


def resized(image: Image.Image, side: int) -> Image.Image:
    return image.resize((side, side), Image.LANCZOS)


def main() -> None:
    logo = tight_square(Image.open(MASTER).convert("RGBA"))
    PACKAGE_ASSETS.mkdir(parents=True, exist_ok=True)

    frames = [resized(logo, side) for side in ICON_SIZES]
    frames[-1].save(
        PACKAGE_ASSETS / "icon.ico",
        format="ICO",
        sizes=[frame.size for frame in frames],
        append_images=frames[:-1],
    )
    for side in WINDOW_ICON_SIZES:
        resized(logo, side).save(PACKAGE_ASSETS / f"icon-{side}.png")
    for side in UI_LOGO_SIZES:
        resized(logo, side).save(PACKAGE_ASSETS / f"logo-{side}.png")
    resized(logo, README_LOGO_SIZE).save(README_LOGO, optimize=True)


if __name__ == "__main__":
    main()
