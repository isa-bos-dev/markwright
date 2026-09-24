"""Guard tests: fail when unused translation keys or assets creep back into the repository."""

import ast
import re
from collections.abc import Iterable
from pathlib import Path

from markwright.core.converter import ConversionStage
from markwright.i18n.strings import STRINGS

_SOURCE = Path(__file__).resolve().parents[1] / "src" / "markwright"
_ASSETS_DIR = _SOURCE / "assets"
_TRANSLATIONS_MODULE = _SOURCE / "i18n" / "strings.py"

# Assets used by something other than the Python code, each with the reason. A stale
# entry (the file no longer exists) fails the suite, so this list cannot rot.
_ASSETS_USED_OUTSIDE_PYTHON = {
    "icon.ico": "embedded in the Windows executable by the packaging build (REL)",
}


def _docstring_constants(tree: ast.Module) -> set[int]:
    """Ids of the string nodes that are docstrings (prose, not real usage)."""
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                docstrings.add(id(first.value))
    return docstrings


def _strings_used_in(sources: Iterable[Path]) -> tuple[set[str], list[ast.JoinedStr]]:
    """Every string literal and f-string that the given modules contain."""
    literals: set[str] = set()
    templates: list[ast.JoinedStr] = []
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = _docstring_constants(tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docstrings
            ):
                literals.add(node.value)
            elif isinstance(node, ast.JoinedStr):
                templates.append(node)
    return literals, templates


def _keys_built_by(template: ast.JoinedStr) -> set[str]:
    """Translation keys an f-string can produce: its prefix plus each possible ending.

    The endings are the string literals inside the placeholder (``{'a' if x else 'b'}``);
    a placeholder without literals is the progress stage (``progress.{stage.value}``).
    """
    first = template.values[0] if template.values else None
    if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
        return set()
    endings = {
        node.value
        for part in template.values
        if isinstance(part, ast.FormattedValue)
        for node in ast.walk(part.value)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    endings = endings or {stage.value for stage in ConversionStage}
    return {first.value + ending for ending in endings}


def _file_names_matched_by(template: ast.JoinedStr) -> re.Pattern[str] | None:
    """A pattern for the file names an f-string can produce (``icon-{side}.png``)."""
    if not any(isinstance(p, ast.Constant) and p.value for p in template.values):
        return None  # A bare ``f"{value}"`` would match every asset and hide orphans.
    parts = [
        re.escape(str(part.value)) if isinstance(part, ast.Constant) else ".+"
        for part in template.values
    ]
    return re.compile("".join(parts))


def find_unused_translation_keys(keys: Iterable[str], sources: Iterable[Path]) -> set[str]:
    literals, templates = _strings_used_in(sources)
    used = set(literals)
    for template in templates:
        used |= _keys_built_by(template)
    return set(keys) - used


def find_unreferenced_assets(
    names: Iterable[str], sources: Iterable[Path], used_elsewhere: Iterable[str] = ()
) -> set[str]:
    literals, templates = _strings_used_in(sources)
    patterns = [p for p in map(_file_names_matched_by, templates) if p is not None]
    return {
        name
        for name in names
        if name not in literals
        and name not in set(used_elsewhere)
        and not any(pattern.fullmatch(name) for pattern in patterns)
    }


def _production_sources() -> list[Path]:
    return [path for path in sorted(_SOURCE.rglob("*.py")) if path != _TRANSLATIONS_MODULE]


def _packaged_asset_names() -> set[str]:
    return {path.name for path in _ASSETS_DIR.iterdir() if path.is_file()}


# --- The repository itself ---


def test_every_translation_key_is_used_by_the_code() -> None:
    keys = {key for table in STRINGS.values() for key in table}

    assert find_unused_translation_keys(keys, _production_sources()) == set()


def test_every_packaged_asset_is_referenced() -> None:
    unreferenced = find_unreferenced_assets(
        _packaged_asset_names(), _production_sources(), _ASSETS_USED_OUTSIDE_PYTHON
    )

    assert unreferenced == set()


def test_the_assets_used_outside_python_list_has_no_stale_entries() -> None:
    assert set(_ASSETS_USED_OUTSIDE_PYTHON) <= _packaged_asset_names()


# --- The detectors: they must fail when they should ---


def _module(tmp_path: Path, source: str) -> list[Path]:
    path = tmp_path / "module.py"
    path.write_text(source, encoding="utf-8")
    return [path]


def test_an_unused_translation_key_is_reported(tmp_path: Path) -> None:
    sources = _module(tmp_path, 'label = t("a.used")\n')

    assert find_unused_translation_keys({"a.used", "a.orphan"}, sources) == {"a.orphan"}


def test_a_key_that_only_appears_in_a_docstring_counts_as_unused(tmp_path: Path) -> None:
    sources = _module(tmp_path, 'def f():\n    """Mentions a.orphan in prose."""\n')

    assert find_unused_translation_keys({"a.orphan"}, sources) == {"a.orphan"}


def test_keys_built_from_literal_choices_in_an_f_string_are_recognised(tmp_path: Path) -> None:
    sources = _module(tmp_path, "key = f\"x.{'one' if flag else 'two'}\"\n")

    unused = find_unused_translation_keys({"x.one", "x.two", "x.three"}, sources)

    assert unused == {"x.three"}


def test_keys_built_from_the_progress_stage_are_recognised(tmp_path: Path) -> None:
    sources = _module(tmp_path, 'key = f"progress.{stage.value}"\n')

    unused = find_unused_translation_keys({"progress.started", "progress.nope"}, sources)

    assert unused == {"progress.nope"}


def test_an_unreferenced_asset_is_reported(tmp_path: Path) -> None:
    sources = _module(tmp_path, 'load("logo.png")\nload(f"icon-{side}.png")\n')

    unreferenced = find_unreferenced_assets({"logo.png", "icon-32.png", "old.png"}, sources)

    assert unreferenced == {"old.png"}


def test_a_bare_placeholder_f_string_does_not_hide_unreferenced_assets(tmp_path: Path) -> None:
    sources = _module(tmp_path, 'message = f"{value}"\n')

    assert find_unreferenced_assets({"old.png"}, sources) == {"old.png"}


def test_an_asset_declared_as_used_outside_python_is_not_reported(tmp_path: Path) -> None:
    sources = _module(tmp_path, "pass\n")

    unreferenced = find_unreferenced_assets({"icon.ico"}, sources, used_elsewhere={"icon.ico"})

    assert unreferenced == set()
