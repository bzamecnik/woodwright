# Installation

woodwright needs Python 3.14. Which way to install it depends on whether
you only want to use the `woodwright` command or also write Python with it.

## Without programming: uv

You don't need to know Python to try woodwright: one small program,
[uv](https://docs.astral.sh/uv/), installs it with everything it needs,
and you then type a few commands.

1. **Open a terminal**: Terminal on macOS (in Applications / Utilities),
   PowerShell on Windows (from the Start menu), any terminal on Linux.
2. **Install uv** by pasting this line into it and pressing Enter:

    === "macOS and Linux"

        ```shell
        curl -LsSf https://astral.sh/uv/install.sh | sh
        ```

    === "Windows"

        ```shell
        powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
        ```

    Then close the terminal and open a new one.

3. **Check that it works** by listing the examples (the first run downloads
   Python and woodwright, which takes a minute):

    ```shell
    uvx --python 3.14 woodwright list
    ```

`uvx` runs woodwright without installing it for good: put
`uvx --python 3.14` in front of each `woodwright` command in these docs.
The `--python 3.14` makes sure uv doesn't pick an older Python you may
already have. To update woodwright later, write `woodwright@latest` instead
of `woodwright` once:

```shell
uvx --python 3.14 woodwright@latest list
```

Next: [export the examples](tutorials/examples.md).

## In a Python project

```shell
uv add woodwright      # or: pip install woodwright
```

The package gives you the library (`import woodwright as ww`) and the
`woodwright` command.

## Viewing models in 3D

The exported STL and STEP files open in any 3D viewer or CAD program, e.g.
the free [FreeCAD](https://www.freecad.org/) or an online STL viewer.

To look at models while you write them, use a Jupyter notebook with
[jupyter-cadquery](https://github.com/bernhard-42/jupyter-cadquery), which
shows build123d shapes in an interactive viewer:

```shell
uv add --dev jupyter jupyter-cadquery
uv run jupyter lab
```

In a notebook, a shape as the last expression of a cell is shown in 3D:

```py
import jupyter_cadquery  # registers the viewer
from woodwright.examples import frames

frames.mortise_tenon_frame(rail_length=400).resolve().compound()
```

`notebooks/examples.ipynb` in the repository shows a few examples this way.

## From source

To work on woodwright itself:

```shell
git clone https://github.com/bzamecnik/woodwright
cd woodwright
uv sync                    # the environment, with pytest and ruff
uv sync --group notebook   # and Jupyter with the 3D viewer
uv sync --group docs       # and the tools to build these docs
uv run pytest
```

The documentation is built locally:

```shell
uv run docs/gallery.py                  # the example gallery, from output/
uv run --group docs zensical serve      # at http://localhost:8000
```

The gallery shows the examples you have exported to `output/`: export them
first (`uv run woodwright export --all`, a few minutes) to see their
pictures, drawings and plans. Without them the gallery still lists every
example with its parameters and code.
