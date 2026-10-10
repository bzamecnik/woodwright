# woodwright

A semantic CAD library for woodworking.
See [docs/vision.md](docs/vision.md).

## Setup

Install the environment and dependencies:
```shell
uv sync
pre-commit install  # ruff lint + format on commit
```

## Development

```shell
uv run pytest
uv run ruff format
uv run ruff check --fix
```

## Examples

```sh
# outputs (STL/STEP/SVG written) to output/
uv run python examples/mortise_tenon.py
uv run python examples/dovetail_corner.py
```
