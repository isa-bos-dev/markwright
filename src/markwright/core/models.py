import os
import sys
from pathlib import Path

MODELS_DIR_ENV_VAR = "MARKWRIGHT_MODELS_DIR"
_MODELS_FOLDER_NAME = "models"


def find_models_dir() -> Path | None:
    """Locate a local folder with the ML models, so conversions can run fully offline.

    Priority: the MARKWRIGHT_MODELS_DIR variable, a ``models`` folder next to the
    packaged executable, then ``models`` in the working directory. Only existing
    directories count; ``None`` means docling keeps its own defaults.
    """
    candidates: list[Path] = []
    configured = os.environ.get(MODELS_DIR_ENV_VAR)
    if configured:
        candidates.append(Path(configured))
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).parent / _MODELS_FOLDER_NAME)
    candidates.append(Path.cwd() / _MODELS_FOLDER_NAME)
    return next((path for path in candidates if path.is_dir()), None)
