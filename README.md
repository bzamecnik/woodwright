# woodwright

A semantic CAD library for woodworking. You describe furniture the way a
woodworker thinks about it: boards and rods with named sides, and the
joints between them. woodwright works out the joinery, the cut sizes and where every part
goes, and produces 3D models (STEP, STL), drawings (SVG) and cut lists.

It is built on [build123d](https://github.com/gumyr/build123d). This is an
early alpha: the API will still change.

<table>
  <tr>
    <td><a href="https://github.com/bzamecnik/woodwright/blob/master/docs/images/chair.svg"><img src="https://raw.githubusercontent.com/bzamecnik/woodwright/master/docs/images/chair.svg" height="450" alt="A chair drawn by woodwright"></a></td>
    <td><a href="https://github.com/bzamecnik/woodwright/blob/master/docs/images/chair_exploded.svg"><img src="https://raw.githubusercontent.com/bzamecnik/woodwright/master/docs/images/chair_exploded.svg" height="450" alt="The chair taken apart, showing its tenons and mortises"></a></td>
  </tr>
  <tr>
    <td colspan="2">A chair with mortise-and-tenon joints, assembled and exploded:
    <a href="https://github.com/bzamecnik/woodwright/blob/master/src/woodwright/examples/projects.py">projects.chair</a>
    in the example library. Every tenon and mortise is derived from the
    joints between the parts.</td>
  </tr>
  <tr>
    <td><a href="https://github.com/bzamecnik/woodwright/blob/master/docs/images/workbench.svg"><img src="https://raw.githubusercontent.com/bzamecnik/woodwright/master/docs/images/workbench.svg" width="420" alt="A workbench drawn by woodwright"></a></td>
    <td><a href="https://github.com/bzamecnik/woodwright/blob/master/docs/images/workbench_exploded.svg"><img src="https://raw.githubusercontent.com/bzamecnik/woodwright/master/docs/images/workbench_exploded.svg" width="420" alt="The workbench taken apart, showing its laps, tusk tenons and dowels"></a></td>
  </tr>
  <tr>
    <td colspan="2">A knock-down workbench after
    <a href="https://rexkrueger.com">Rex Krueger</a>'s Quick Stack Workbench, assembled and exploded:
    <a href="https://github.com/bzamecnik/woodwright/blob/master/src/woodwright/examples/projects.py">projects.workbench</a>.
    Laminated legs and rails, half-dovetailed laps, stretchers held by tapered dowel tusks,
    a desk of beams on edge and a tray that turns over into a flat top. This is only a rough
    approximation with different dimensions: get Rex's <a href="https://www.rexkrueger.com/store/p/quick-stack-workbench">plans</a> for the real thing with detailed instructions if you want to build one.</td>
  </tr>
</table>

## Getting started without programming

You don't need to know Python to try woodwright: one small program, uv,
installs it with everything it needs, and you then type a few commands.

1. **Open a terminal**: Terminal on macOS (in Applications / Utilities),
   PowerShell on Windows (from the Start menu), any terminal on Linux.
2. **Install [uv](https://docs.astral.sh/uv/getting-started/installation/)**
   by pasting this line into it and pressing Enter.
   - macOS and Linux:
     ```shell
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```
   - Windows:
     ```shell
     powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
     ```

   Then close the terminal and open a new one.
3. **List the examples**, from single joints to whole projects (the first
   run downloads Python and woodwright, which takes a minute):
   ```shell
   uvx --python 3.14 woodwright list
   ```
4. **Export one**, e.g. a small cabinet door:
   ```shell
   uvx --python 3.14 woodwright export projects.cabinet_door
   ```
   This makes a folder `output/projects/cabinet_door` in the folder the
   terminal is in (your home folder, unless you moved with `cd`). In it:
   - `cut_list.txt` – each part with its size and its cuts (tenons, mortises,
     grooves...), a plain text file;
   - `drawings/` – shop drawings to build from, open them in a web browser
     and print them (A4): a sheet for each part with its views, dimensions
     in mm and its cuts numbered and described; the whole thing with its
     overall size; its parts numbered on an exploded view, with a parts list;
   - `.svg` pictures of the whole thing, an exploded view and each part;
   - `.stl` 3D models of the whole thing and each part – open them in any
     online STL viewer;
   - `assembled.step` – the 3D model for CAD programs such as the free
     [FreeCAD](https://www.freecad.org/), which opens the `.stl` files too.
5. **Make your own**: in a plain text editor (TextEdit set to plain text,
   Notepad, ...) write a file `my_door.py` with the sizes you want:
   ```python
   from woodwright.examples import projects

   door = projects.cabinet_door(height=700, width=450)
   ```
   and export it, in the folder where you saved it:
   ```shell
   uvx --python 3.14 woodwright export my_door.py
   ```
   The results are in `output/my_door/door`. What each example can change
   (sizes, stock thickness...) is listed at the top of its code in
   [the example library](https://github.com/bzamecnik/woodwright/tree/HEAD/src/woodwright/examples);
   copying an example's code into your file is the way on to your own designs.

To update woodwright later, write `woodwright@latest` instead of `woodwright`
once. If you use an AI coding assistant (e.g. Claude Code), you can also ask
it to do all of this for you.

## Installation

```shell
pip install woodwright  # or: uv add woodwright
```

Requires Python 3.14. The `woodwright` command lists and exports the
examples and your own design files (`woodwright --help`). Source: <https://github.com/bzamecnik/woodwright>

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
export_model(model, Path("output/corner"))  # STEP, STL, SVG views, drawings, cut list
```

```text
stile  600 x 60 x 20 mm  oak
       - mortise 50 x 8 mm, 42 deep, in stile.back_edge
rail   340 x 60 x 20 mm  oak
       - tenon 50 x 8 mm, 40 long, on rail.left_end
```

What's there so far:

- **Stock:** boards, and round rods (dowels, pegs, rungs, round legs).
- **Cuts:** grooves, dados and rabbets (through or stopped), mortises, slot
  mortises, tenons (haunched, mitred, chamfered, multiple side by side or
  across the thickness, wedged), tongues, dovetail tongues and laps,
  chamfers, mitres (across the face, the edge, or along the grain), tapers;
  holes (through, blind, counterbored, countersunk, tapered), round tenons
  (tapered, chamfered, with a kerf for a wedge), end chamfers, round tapers
  and flats on rods.
- **Joints:** butt (also turned at an angle); dado, rabbet, groove and
  tongue and groove housings (also stopped); mortise and tenon (blind,
  through, stub, haunched, mitred, with mitred shoulders, multiple, wedged,
  tusk, pinned, drawbored); loose tenons and loose tongues; bridles (L and
  T); half laps (plain, dovetailed, mitred), cross laps, mitred face
  tenons; box joints; sliding, through, half-blind, mitred-corner and blind
  mitred dovetails; mitre corners and splices, keyed mitres (straight,
  dovetailed or slanted keys across the corner), splined mitres (along the
  corner or the mitre line, through or stopped); butterfly keys across a
  crack or the joint of two boards; table-top buttons; round
  tenons and whole rods in holes (blind, through, tapered, wedged, into
  square or round stock); dowels; screws (clearance and pilot holes,
  countersunk or counterbored).

## Example library

`woodwright.examples` holds over 140 examples, from single cuts through
joints to projects: a try square, a mallet, a bookshelf, a dovetailed drawer
with a bottom, a dining table, a side table, a chair, a stool and a step
stool on round legs wedged through their seats, a towel rail, a coat rack
with pegs, ledged and frame-and-panel doors, a small glazed cabinet door, a
knock-down workbench after Rex Krueger's Quick Stack (get his plans for the
real thing).

```shell
woodwright list
woodwright export projects.chair --out output
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
