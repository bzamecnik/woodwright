# CLAUDE.md

Semantic CAD library for woodworking: a textual language describing furniture parts, joints, constraints and manufacturing, producing 3D models, cut lists, drawings and instructions. See `docs/vision.md` for the vision, `docs/initial_vision.md` for background.

## Commands

- `uv sync` – install the environment (Python 3.14, uv project)
- `uv run python examples/<name>.py` – examples, they write to `output/`
- `uv run pytest` – run tests
- `uv run ruff format` / `uv run ruff check --fix` – format and lint (also run by the pre-commit hook: `pre-commit install`)

## Conventions

- Source in `src/woodwright/`, tests in `tests/` (pytest), examples in `examples/`.
- Use type hints wherever they help (public functions, dataclasses); don't contort code to satisfy the checker.
- Commit coherent pieces of work separately, with a descriptive message.
