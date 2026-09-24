"""Guard tests: fail when unused code, resources or undeclared dependencies creep back in."""

import ast
import re
import sys
import tomllib
from collections.abc import Iterable, Mapping
from importlib.metadata import packages_distributions, requires
from pathlib import Path

from markwright.core.converter import ConversionStage
from markwright.i18n.strings import STRINGS

_ROOT = Path(__file__).resolve().parents[1]
_SOURCE = _ROOT / "src" / "markwright"
_FIRST_PARTY_PACKAGE = "markwright"
_ASSETS_DIR = _SOURCE / "assets"
_TRANSLATIONS_MODULE = _SOURCE / "i18n" / "strings.py"

# Distribution that ships a module -> the distribution a project declares to get it.
# ``docling`` is a meta-package: it only installs ``docling-slim``, which holds the code.
# The suite checks each pair against the installed metadata, so this cannot rot.
_INSTALLED_BY = {"docling-slim": "docling"}

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


def _normalize(distribution: str) -> str:
    """The canonical spelling of a distribution name (PEP 503)."""
    return re.sub(r"[-_.]+", "-", distribution).lower()


def _requirement_names(requirements: Iterable[object]) -> set[str]:
    """Distribution names in a list of requirement strings (``"docling>=2.1"`` -> docling)."""
    names = set()
    for requirement in requirements:
        match = (
            re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", requirement)
            if isinstance(requirement, str)
            else None
        )
        if match:
            names.add(_normalize(match.group(0)))
    return names


def declared_dependencies(pyproject: Path) -> tuple[set[str], set[str]]:
    """The runtime and the development dependencies declared in ``pyproject.toml``."""
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    runtime = _requirement_names(data.get("project", {}).get("dependencies", []))
    development = _requirement_names(data.get("dependency-groups", {}).get("dev", []))
    return runtime, development


def _imported_top_level_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def find_undeclared_imports(
    sources: Iterable[Path],
    declared: set[str],
    local_modules: Iterable[str] = (),
    distributions: Mapping[str, list[str]] | None = None,
) -> dict[str, list[str]]:
    """Third-party modules imported without being declared: ``{module: [files]}``.

    A module is matched to its distribution through the installed metadata
    (``PIL`` -> ``pillow``), so no hand-kept translation table can drift.
    """
    if distributions is None:
        distributions = packages_distributions()
    local = set(local_modules) | {_FIRST_PARTY_PACKAGE}
    undeclared: dict[str, set[str]] = {}
    for path in sources:
        for module in _imported_top_level_modules(path):
            if module in sys.stdlib_module_names or module in local:
                continue
            owners = {_normalize(name) for name in distributions.get(module, [])}
            owners |= {_INSTALLED_BY[name] for name in owners if name in _INSTALLED_BY}
            if not owners & declared:
                undeclared.setdefault(module, set()).add(path.name)
    return {module: sorted(files) for module, files in sorted(undeclared.items())}


def _python_files(*folders: Path) -> list[Path]:
    return [path for folder in folders for path in sorted(folder.rglob("*.py"))]


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


def test_every_meta_package_alias_matches_the_installed_metadata() -> None:
    for shipped_by, declared in _INSTALLED_BY.items():
        assert shipped_by in _requirement_names(requires(declared) or [])


def test_every_third_party_library_the_application_imports_is_a_declared_dependency() -> None:
    runtime, _ = declared_dependencies(_ROOT / "pyproject.toml")

    undeclared = find_undeclared_imports(_python_files(_SOURCE), runtime)

    assert undeclared == {}


def test_every_third_party_library_tests_and_scripts_import_is_declared() -> None:
    runtime, development = declared_dependencies(_ROOT / "pyproject.toml")
    folders = [_ROOT / "tests", _ROOT / "scripts"]
    helper_modules = {path.stem for path in _python_files(*folders)}

    undeclared = find_undeclared_imports(
        _python_files(*folders), runtime | development, helper_modules
    )

    assert undeclared == {}


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


_INSTALLED = {"PIL": ["pillow"], "sv_ttk": ["sv-ttk"], "docling_core": ["docling-core"]}


def test_an_undeclared_third_party_import_is_reported_with_its_file(tmp_path: Path) -> None:
    sources = _module(tmp_path, "import docling_core\nfrom PIL import Image\n")

    undeclared = find_undeclared_imports(sources, {"pillow"}, distributions=_INSTALLED)

    assert undeclared == {"docling_core": ["module.py"]}


def test_a_submodule_import_is_matched_by_its_top_level_package(tmp_path: Path) -> None:
    sources = _module(tmp_path, "from docling_core.types.doc import DoclingDocument\n")

    undeclared = find_undeclared_imports(sources, set(), distributions=_INSTALLED)

    assert undeclared == {"docling_core": ["module.py"]}


def test_a_module_shipped_by_a_meta_package_dependency_counts_as_declared(
    tmp_path: Path,
) -> None:
    sources = _module(tmp_path, "import docling\n")

    undeclared = find_undeclared_imports(
        sources, {"docling"}, distributions={"docling": ["docling-slim"]}
    )

    assert undeclared == {}


def test_a_module_that_maps_to_no_installed_distribution_is_reported(tmp_path: Path) -> None:
    sources = _module(tmp_path, "import mystery\n")

    undeclared = find_undeclared_imports(sources, {"pillow"}, distributions=_INSTALLED)

    assert undeclared == {"mystery": ["module.py"]}


def test_a_declared_import_is_matched_whatever_its_module_and_distribution_spelling(
    tmp_path: Path,
) -> None:
    sources = _module(tmp_path, "import sv_ttk\n")

    undeclared = find_undeclared_imports(sources, {"sv-ttk"}, distributions=_INSTALLED)

    assert undeclared == {}


def test_standard_library_first_party_and_local_helper_imports_are_ignored(
    tmp_path: Path,
) -> None:
    sources = _module(
        tmp_path,
        "import os\nimport markwright\nimport conftest\nfrom . import sibling\nfrom .x import y\n",
    )

    undeclared = find_undeclared_imports(
        sources, set(), local_modules={"conftest"}, distributions=_INSTALLED
    )

    assert undeclared == {}


def test_dependencies_are_read_from_pyproject_with_normalised_names(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\ndependencies = ["Sv_TTK>=2.6", "docling[extra]>=2"]\n'
        '[dependency-groups]\ndev = ["pytest>=9", {include-group = "other"}]\n',
        encoding="utf-8",
    )

    runtime, development = declared_dependencies(pyproject)

    assert runtime == {"sv-ttk", "docling"}
    assert development == {"pytest"}


def test_an_asset_declared_as_used_outside_python_is_not_reported(tmp_path: Path) -> None:
    sources = _module(tmp_path, "pass\n")

    unreferenced = find_unreferenced_assets({"icon.ico"}, sources, used_elsewhere={"icon.ico"})

    assert unreferenced == set()
