from dataclasses import dataclass
from pathlib import Path

from markwright.core.exceptions import OutputWriteError

MAX_COLLISION_ATTEMPTS = 1000


@dataclass(frozen=True)
class OutputPaths:
    markdown_path: Path
    images_dir: Path


def resolve_output_paths(input_path: Path, output_path: Path | None = None) -> OutputPaths:
    """Compute the final .md and images-folder paths, applying the collision strategy.

    This function never touches the filesystem beyond read-only existence
    checks: it does not create files or directories.
    """
    input_path = Path(input_path).resolve()

    if output_path is not None:
        candidate = Path(output_path).resolve()
        # Checked before suffix normalization: a directory has no meaningful
        # ".md" rewrite, so it must fail fast rather than produce a confusing
        # sibling filename.
        if candidate.is_dir():
            raise OutputWriteError(candidate)
        if candidate.suffix.lower() != ".md":
            candidate = candidate.with_suffix(".md")
        directory = candidate.parent
        stem = candidate.stem
    else:
        directory = input_path.parent
        stem = input_path.stem

    if not directory.is_dir():
        raise OutputWriteError(directory)

    for attempt in range(MAX_COLLISION_ATTEMPTS):
        candidate_stem = stem if attempt == 0 else f"{stem}_{attempt}"
        markdown_path = directory / f"{candidate_stem}.md"
        images_dir = directory / f"{candidate_stem}_images"
        if not markdown_path.exists() and not images_dir.exists():
            return OutputPaths(markdown_path=markdown_path, images_dir=images_dir)

    raise OutputWriteError(directory / stem)
