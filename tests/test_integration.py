"""Real end-to-end conversion with the actual models (slow).

Excluded from the default run. Run it from the project root, where ``models/`` lives:

    uv run pytest -m integration
"""

from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from markwright.core.converter import ConversionStage, convert_pdf_to_md
from markwright.core.models import find_models_dir

pytestmark = pytest.mark.integration


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    page = Image.new("RGB", (1240, 500), "white")
    font = ImageFont.load_default(size=72)
    ImageDraw.Draw(page).text((100, 150), "Markwright integration test", fill="black", font=font)
    path = tmp_path / "sample.pdf"
    page.save(path, "PDF", resolution=150)
    return path


def test_a_real_conversion_reads_the_text_of_the_page_without_going_online(
    sample_pdf: Path,
) -> None:
    if find_models_dir() is None:
        pytest.skip("no local models folder (run from the project root or set the env var)")
    stages: list[ConversionStage] = []

    output = convert_pdf_to_md(
        sample_pdf, on_progress=lambda stage, warning=None: stages.append(stage)
    )

    assert "markwright" in output.read_text(encoding="utf-8").lower()
    assert stages[0] == ConversionStage.STARTED
    assert stages[-1] == ConversionStage.DONE
