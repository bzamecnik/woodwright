# CLAUDE.md

Semantic CAD library for woodworking: a textual language describing furniture parts, joints, constraints and manufacturing, producing 3D models, cut lists, drawings and instructions. See `docs/vision.md` for the vision, `docs/initial_vision.md` for background.

## Commands

- `uv sync` – install the environment (Python 3.14, uv project)
- `uv sync --group notebook` – also install `jupyter` and `jupyter-cadquery` for interactive viewing
- `uv run woodwright {list,export}` – the example library (`src/woodwright/examples/`) and design files (`woodwright export my_door.py`), exports to `output/`
- `uv run pytest` – run tests
- `uv run docs/gallery.py && uv run --group docs zensical serve` – the docs site (Zensical, `mkdocs.yml`, pages in `docs/`); the example gallery is generated from the exports in `output/` (re-export examples to refresh it), stale ones are reported
- Release: bump `version` in `pyproject.toml`, commit, push a tag `vX.Y.Z` – GitHub Actions (`.github/workflows/release.yml`) tests, publishes on PyPI and deploys the docs on GitHub Pages; CI (`ci.yml`) runs on pushes to master and PRs
- `uv run ruff format` / `uv run ruff check --fix` – format and lint (also run by the pre-commit hook: `pre-commit install`)

## Conventions

- Source in `src/woodwright/`, tests in `tests/` (pytest), the example library in `src/woodwright/examples/`.
- Use type hints wherever they help (public functions, dataclasses); don't contort code to satisfy the checker.
- Commit coherent pieces of work separately, with a descriptive message.
- Docs pages' ```python blocks are run by `tests/test_docs.py` (printed output must match the ```text block after); use ```py for fragments.
- After adding or changing examples, export them to `output/` for the user, listing them by name
  (`uv run woodwright export cuts.dowel cuts.peg ...`), so they can open the results straight away.
