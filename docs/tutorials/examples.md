# Export the examples

woodwright comes with a library of over 140 examples: single cuts, joints,
frames and whole projects. Each one can be exported to files to look at,
print and build from. (If you haven't installed woodwright, put
`uvx --python 3.14` in front of each `woodwright` below; see
[Installation](../install.md).)

## List them

```shell
woodwright list
```

```text
cuts.dado                                A dado: a groove across the grain, from edge to edge.
...
projects.cabinet_door                    A small cabinet door of 2 x 3 cm stock with mitred shoulder tenons,
projects.table                           A table: legs and wide aprons, a solid top held down by buttons; outside sizes.
...
```

Each example has a name of two words: its group (`cuts`, `joints`,
`frames`, `projects`) and its own name. The same list with pictures is the
[example gallery](../gallery/index.md).

## Export one

```shell
woodwright export projects.cabinet_door
```

This makes a folder `output/projects/cabinet_door` in the folder the
terminal is in (your home folder, unless you moved with `cd`). In it:

- `plans.pdf`: the plans in one PDF, to print or send: a cover, contents,
  all the drawings below, the cut list and the code they were made from;
- `cut_list.txt`: each part with its size and its cuts (tenons, mortises,
  grooves...), a plain text file;
- `drawings/`: shop drawings to build from; open them in a web browser and
  print them (A4): a sheet for each part with its views, dimensions in mm
  and its cuts numbered and described; the whole thing with its overall
  size; its parts numbered on an exploded view, with a parts list;
- `.svg` pictures of the whole thing, an exploded view and each part;
- `.stl` 3D models of the whole thing and each part, for any STL viewer;
- `assembled.step`: the 3D model for CAD programs such as the free
  [FreeCAD](https://www.freecad.org/), which opens the `.stl` files too.

[Outputs](../guide/outputs.md) describes them in detail.

## Export several, or all

```shell
woodwright export joints.dovetail_corner joints.mortise_tenon frames.bridle_frame
woodwright export --all                  # every example: a few minutes
woodwright export --all --out examples   # into another folder than output/
```

The pictures and drawings take most of the time. Without them
(`--no-views`) you get the 3D models and the cut list in seconds:

```shell
woodwright export projects.table --no-views
```

Next: [change an example](parameters.md) to the sizes you need.
