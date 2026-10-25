# Command line

The `woodwright` command lists the examples and exports them, or your own
design files, to STEP, STL, SVG views, shop drawings, the plans PDF and the
cut list.

```shell
woodwright list
woodwright export projects.cabinet_door
woodwright export my_door.py
woodwright export my_door.py:door
woodwright export --all --out build/examples
```

Without installing woodwright, put `uvx --python 3.14` in front (see
[Installation](../install.md)).

## `woodwright list`

Each example by name (`module.function`), with the first line of its
description. The same with pictures: the [example gallery](../gallery/index.md).

## `woodwright export`

```text
usage: woodwright export [-h] [--all] [--out OUT] [--no-views] [names ...]

positional arguments:
  names       examples (e.g. frames.bridle_frame) or design files (my_door.py,
              my_door.py:door)

options:
  -h, --help  show this help message and exit
  --all       export all examples
  --out OUT   default: output
  --no-views  skip the (slow) SVG views and drawings
```

An example goes to `<out>/<module>/<function>`, e.g.
`output/projects/cabinet_door`. A design file is a Python file defining
assemblies: each `Assembly` assigned to a variable, and each function
defined in it that returns one and needs no arguments (annotated
`-> Assembly`), is exported to `<out>/<file name>/<name>`. Names starting
with an underscore are left out. With `my_door.py:door` only the one named
is exported.

What lands in the folder is described in [Outputs](../guide/outputs.md).
