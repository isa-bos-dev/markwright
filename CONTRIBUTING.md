# Contributing to Markwright

Thanks for considering contributing. This is currently a single-maintainer
project, so please open an issue to discuss anything beyond a small fix before
putting significant work into a pull request — it avoids wasted effort on both
sides.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Setting up the development environment

```bash
git clone https://github.com/isa-bos-dev/markwright.git
cd markwright
uv sync
```

Run the app while developing with `uv run markwright ...` (see the README for the
two ways to run it: CLI, interactive menu).

## Before opening a pull request

All of the following must pass:

```bash
uv run pytest              # fast suite (mocked conversions)
uv run pytest --cov        # same, with the coverage threshold enforced (slower)
uv run ruff format .
uv run ruff check .
uv run mypy
```

The fast suite mocks the actual PDF conversion, so it doesn't need any ML models
on disk and runs in a few seconds. There is also a real, offline, end-to-end
integration test, skipped by default because it needs local models:

```bash
uv run pytest -m integration
```

You don't need to run it unless you're changing `core/converter.py` itself.

## Code style

- Enforced by `ruff` (formatting and linting) and `mypy` (type checking on
  `src/`) — configuration lives in `pyproject.toml`, nothing to configure
  yourself.
- Type hints are required in `src/`, not in `tests/` or `scripts/`.
- Match the style of the surrounding code (naming, comment density, test
  structure) rather than introducing a new pattern for the same kind of problem.

## Commit messages

Short, imperative, with a conventional-commits-style prefix matching the
existing history — `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`,
`build:`. No AI-attribution trailers.

## License

By contributing, you agree that your contribution is licensed under this
project's [Apache-2.0 license](LICENSE).
