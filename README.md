# woodwright

A semantic CAD library for woodworking. You describe furniture the way a
woodworker thinks about it: boards with named sides, and the joints between
them. woodwright works out the joinery, the cut sizes and where every part
goes, and produces 3D models (STEP, STL), drawings (SVG) and cut lists.

It is built on [build123d](https://github.com/gumyr/build123d). This is an
early alpha: the API will still change.

## Installation

```shell
pip install woodwright  # or: uv add woodwright
```

Requires Python 3.14. Source: <https://github.com/bzamecnik/woodwright>

## Quickstart

A rail tenoned into a stile. You give the design dimensions and the joint;
the tenon, the mortise, the rail's cut length and its placement are derived.

```python
from pathlib import Path

import woodwright as ww
from woodwright.export import export_model

oak = ww.Stock.board(thickness=20, species="oak")

frame = ww.Assembly("corner", root_location=ww.orient(right_end=ww.UP, back_edge=ww.RIGHT))
stile = frame.add(ww.Board("stile", oak, length=600, width=60))
rail = frame.add(ww.Board("rail", oak, length=300, width=60))  # shoulder to shoulder
frame.join(ww.MortiseTenon(tenon=rail.left_end, mortise=stile.back_edge))

model = frame.resolve()
print(model.cut_list())
export_model(model, Path("output/corner"))  # STEP, STL, SVG views, cut list
```

```text
stile  600 x 60 x 20 mm  oak
       - mortise 50 x 8 mm, 42 deep, in stile.back_edge
rail   340 x 60 x 20 mm  oak
       - tenon 50 x 8 mm, 40 long, on rail.left_end
```

Cuts and joints so far: grooves, dados, rabbets, mortises, tenons (haunched,
mitred), chamfers, mitres, tapers; butt, dado, rabbet, groove, tongue and
groove, mortise and tenon, bridle, half lap, cross lap, mitre corners and
splices, sliding, through and half-blind dovetails, and table-top buttons.

## Example library

`woodwright.examples` holds over fifty examples, from single cuts through
joints to projects: a try square, a mallet, a bookshelf, a dovetailed drawer
with a bottom, a dining table.

```shell
python -m woodwright.examples list
python -m woodwright.examples export projects.table --out output
```

The design ideas are in [docs/vision.md](https://github.com/bzamecnik/woodwright/blob/HEAD/docs/vision.md)
and [docs/plan.md](https://github.com/bzamecnik/woodwright/blob/HEAD/docs/plan.md).

## Development

Install the environment and dependencies:
```shell
uv sync
pre-commit install  # ruff lint + format on commit
```

Optionally, for notebooks with an interactive 3D viewer:
```shell
uv sync --group notebook
uv run jupyter lab
```

Run the tests and the linters:
```shell
uv run pytest
uv run ruff format
uv run ruff check --fix
```

## License

[MIT License](./LICENSE).

### Credits

- Ideas and guidance: Bohumír Zámečník
- Most of the implementation: Claude Code (Opus 5.5)
