import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from markwright.i18n import SUPPORTED_LANGUAGES

_log = logging.getLogger(__name__)

THEMES = ("light", "dark")
FONT_SIZES = ("small", "normal", "large")


@dataclass(frozen=True)
class Settings:
    """The user's GUI preferences. The CLI never reads or writes this."""

    language: str = "en"
    theme: str = "light"
    font_size: str = "normal"


DEFAULT_SETTINGS = Settings()


def default_settings_path() -> Path:
    """Where settings live on Windows; falls back to the home folder elsewhere."""
    base = os.environ.get("APPDATA", str(Path.home()))
    return Path(base) / "Markwright" / "settings.json"


def load_settings(path: Path | None = None) -> Settings:
    """Read ``Settings`` from ``path``.

    A missing file, invalid JSON, or an unrecognised value for a field is
    never an error: that field (or the whole result) falls back to its
    default instead. Unknown keys are ignored.
    """
    path = path or default_settings_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return DEFAULT_SETTINGS
    if not isinstance(raw, dict):
        return DEFAULT_SETTINGS

    language = raw.get("language")
    theme = raw.get("theme")
    font_size = raw.get("font_size")
    return Settings(
        language=language if language in SUPPORTED_LANGUAGES else DEFAULT_SETTINGS.language,
        theme=theme if theme in THEMES else DEFAULT_SETTINGS.theme,
        font_size=font_size if font_size in FONT_SIZES else DEFAULT_SETTINGS.font_size,
    )


def save_settings(settings: Settings, path: Path | None = None) -> None:
    """Write ``settings`` to ``path`` atomically.

    Never raises: if the destination cannot be written (missing permissions,
    full disk...), the setting stays applied in memory for this session but
    is not persisted (Constitution Principle 3 — no failure may block the app).
    """
    path = path or default_settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(f"{path.suffix}.tmp")
        tmp_path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
        tmp_path.replace(path)
    except OSError:
        _log.warning("Could not save settings to %s", path)
