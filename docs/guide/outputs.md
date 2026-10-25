# Outputs

`woodwright export` (or `export_model` from Python) writes everything about
a design into one folder. For the table
([projects.table](../gallery/projects/table/index.md)):

```text
output/projects/table/
├── plans.pdf            the plans in one PDF
├── cut_list.txt         the cut list
├── drawings/            shop drawings, one SVG sheet each
│   ├── assembly.svg
│   ├── parts.svg
│   ├── leg.svg
│   ├── apron_front_back.svg
│   └── ...
├── assembled.svg        pictures: the whole, exploded, each part
├── exploded.svg
├── leg_front_left.svg
├── ...
├── assembled.step       3D: the whole for CAD programs
├── assembled.stl        3D: the whole and each part for any viewer
├── leg_front_left.stl
├── ...
└── meta.json            what made these files, for the docs gallery
```

## The plans

`plans.pdf` collects what you need to build the piece, to print or send:

1. a cover with a picture of the piece, its overall size, parts and
   materials, and the date;
2. the contents, with links;
3. the description, if the design has one (`Assembly(description=...)`,
   in Markdown; see [Change an example](../tutorials/parameters.md#a-description-for-the-plans));
4. the shop drawings, below;
5. the cut list;
6. an appendix with the code the plans were made from and the versions
   used, so they can be made again.

## Shop drawings

The sheets in `drawings/` are A4 landscape SVGs; open them in a web browser
and print them at 100 %.

- **Assembly**: front, top and side views of the whole piece with its
  overall size, and an isometric view.
- **Parts**: an exploded view with the parts numbered, and a list of them
  with their cut sizes.
- **A sheet for each part**, one for identical parts: the part lying on
  the bench as you'd mark it out (reference face up, reference edge
  towards you), in views labelled with the side they show (TOP FACE, FRONT
  EDGE, RIGHT END...), so you don't need to know the projection. Its cut
  size is dimensioned outermost; every feature is dimensioned once, chained
  from the ends and the reference sides like marks on a story stick. Each
  feature has a number in a circle, explained in the notes with its
  description from the cut list.

Dimensions are in millimetres, without units. The scale is a standard one
(1:2, 1:5, 1:10...) that fits the sheet; it's in the title block.

## The cut list

`cut_list.txt` lists each part (identical parts once, with their count and
names) with its cut size and species, then its cuts:

```text
leg               720 x 60 x 60 mm  oak, 4 pieces: leg_front_left, leg_front_right, leg_back_right, leg_back_left
                  - mortise 80 x 8 mm, 53 deep, in back_edge
                  - haunch mortise 30 x 8 mm, 10 deep, in back_edge at right_end
                  ...
```

Sizes are length x width x thickness, for a rod its diameter and length.
The cut size includes tenons and anything else the joints add to the
design size. Sides are named as the part lies on the bench (see
[How a design is described](concepts.md#parts-and-their-sides)).

## Pictures and 3D models

- `assembled.svg`, `exploded.svg` and an SVG for each part: hidden-line
  pictures from the front right, a little above, hidden lines dotted.
- `assembled.step`: the assembly with each part as a separate solid, for
  CAD programs (FreeCAD, Fusion, Onshape...).
- `assembled.stl` and an STL for each part: meshes for viewers, 3D printing
  a model, or CAM.

## From Python

```py
from pathlib import Path

from woodwright.export import export_model, svg_view

model = assembly.resolve()
export_model(model, Path("output/my_piece"))  # everything
export_model(model, Path("output/my_piece"), views=False)  # 3D and cut list only, fast
svg_view(model.compound(), Path("picture.svg"))  # one picture
```

The resolved model's shapes are [build123d](https://build123d.readthedocs.io/)
shapes: `model.compound()` for the whole, `model.parts[i].shape` for a part
in its own frame and `.placed_shape` where it is in the assembly. Anything
build123d can do with them (other formats, renders, measurements) works.
See [Export](../reference/export.md) and
[Drawings and plans](../reference/drawing.md) for the details.
