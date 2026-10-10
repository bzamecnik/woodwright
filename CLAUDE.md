# CLAUDE.md

Semantic CAD library for woodworking: a textual language describing furniture parts, joints, constraints and manufacturing, producing 3D models, cut lists, drawings and instructions. See `docs/vision.md` for the vision, `docs/initial_vision.md` for background.

## Commands

- `uv sync` – install the environment (Python 3.14, uv project)
- `python examples/<name>.py` – examples, they write to `output/`

## Conventions

- Source in `src/woodwright/`, examples in `examples/`.
- Use type hints wherever they help (public functions, dataclasses); don't contort code to satisfy the checker.
- Commit coherent pieces of work separately, with a descriptive message.
