from importlib.metadata import PackageNotFoundError, version

APP_NAME = "Markwright"

_FALLBACK_VERSION = "0.0.0+unknown"


def get_version() -> str:
    """The installed package version (``pyproject.toml``'s ``version``, single
    source of truth). Never raises: falls back if metadata isn't available
    (e.g. run as a loose script rather than an installed/editable package)."""
    try:
        return version("markwright")
    except PackageNotFoundError:
        return _FALLBACK_VERSION
