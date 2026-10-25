# How it works

What happens between a design and its files, for those who want to extend
woodwright or understand an odd result. The reasoning behind it is in the
[plan](../plan.md); this is the short version.

## Two layers

woodwright is a layer of woodworking objects on top of
[build123d](https://build123d.readthedocs.io/), a Python CAD library on the
OpenCascade kernel. The woodworking layer (parts, sides, joints, cuts)
decides *where* and *how big*; build123d makes the solids.

Each cut knows how to make its own geometry, in the frame of its part: there
is no central compiler that knows every joint. A new cut or joint is a new
class, and the rest (resolving, the cut list, identical parts, drawings)
works with it unchanged.

## The part frame

Every part has its own frame, in millimetres: the origin on the reference
arris at the left end, x along the length (the grain), y across the width
towards the back edge, z up along the normal of the reference face. A board
fills `[0, length] x [0, width] x [-thickness, 0]`. A rod fills the same
box as a board as wide and thick as its diameter, its axis in the middle.

Cuts are described and made in this frame, so a part's geometry doesn't
depend on where it ends up in the assembly.

## A part is its blank minus its cuts

A part's shape is its **blank**, a box (a cylinder for a rod), with every
**cut's removal** subtracted from it. A tenon is the removal of the waste
around it; a mortise the removal of its hole. Separate pieces (loose
tenons, keys, dowels, wedges) are parts in their own right.

## Resolving

`Assembly.resolve()` turns the design into a `ResolvedModel` without
changing it:

1. **Defaults**: each joint returns a copy of itself with every parameter
   you left out filled in from the [rules](../reference/rules.md) (tenon
   thickness from the stock and a set of chisel widths, mortise depth from
   the part behind it...).
2. **Blanks**: each part starts as its design box. Joints and cuts add
   *allowances* to its sides, e.g. a tenon's length to the rail's end, a
   panel's tongue to its edge, so the blank becomes the cut size.
3. **Placement**: each placing joint gives the location of its second part
   in the frame of its first, from the sides that mate and the sides kept
   flush (`placement.mate`). Starting from the root, placed by
   `root_location`, the locations are chained through the joints. Where a
   second path reaches a part already placed (a loop, like the fourth
   corner of a frame), the two locations must agree. Then the non-placing
   joints (screws, bores, butterflies) get the placement the parts ended up
   in.
4. **Cuts**: each joint, knowing the placement, produces its cuts on both
   parts, e.g. the mortise where the tenon lands, so the two fit by
   construction. The same socket from several joints (a groove taking
   several boards) is cut once.

Up to here no solid is built: dimensions, placements and the list of cuts
come from numbers alone, which is why resolving all the examples takes
under a second.

## Realizing

The solids are built on demand: `ResolvedPart.shape` subtracts the cuts'
removals from the blank (and splits a laminated board into its plies),
`placed_shape` moves it to its location, `ResolvedModel.compound()`
collects them all. This is where OpenCascade does its work, and where the
time goes.

## Identical parts

Two parts are identical when they are of the same kind and stock, with
blanks of the same size, and the shape of one is that of the other turned
over in one of the ways a board can be (end for end, face down, both; a
quarter turn for square stock), compared by their solids. Only a mirror image matching makes them a
mirror pair. Cuts of a part are identical when they differ only in where
they are. See `woodwright.grouping`.

## Drawings and the plans

- **Pictures** are hidden-line projections of the shapes from a viewpoint
  (build123d's `project_to_viewport`), written as SVG.
- **Shop drawings** are generic: for each cut, its removal is intersected
  with the blank, and the faces of that solid inside the blank are the
  surfaces the cut leaves. Their planes give the coordinates to dimension
  (a shoulder, a cheek), cylinders their axes (a hole's centre); the sides
  the solid reaches choose the view. Views are projections along the axes
  of the part frame, so model coordinates map straight onto the drawing.
  Every cut is dimensioned without code of its own, including new ones.
- Drawings are laid out on a `Sheet`, a small layer of lines, circles and
  text in paper millimetres, written to SVG, and drawn natively onto PDF
  pages by [reportlab](https://www.reportlab.com/) for `plans.pdf`.

## Modules

| Module | What's in it |
| --- | --- |
| `woodwright.stock` | `Stock` |
| `woodwright.part` | `Part`, `Board`, `Rod`, sides and arrises |
| `woodwright.placement` | `mate`, positions, `orient` |
| `woodwright.cuts` | the cuts and their removals |
| `woodwright.joints` | the joints: defaults, allowances, placement, cuts |
| `woodwright.rules` | rules of thumb for default dimensions |
| `woodwright.assembly` | `Assembly`, resolving, `ResolvedModel`, the cut list |
| `woodwright.grouping` | identical parts and cuts |
| `woodwright.export` | writing the files, pictures |
| `woodwright.drawing`, `woodwright.sheet` | shop drawings |
| `woodwright.pdf` | the plans PDF |
| `woodwright.cli` | the `woodwright` command |
| `woodwright.examples` | the example library |
