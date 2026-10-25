# A design from scratch

This tutorial builds a frame-and-panel door in Python, step by step: a
frame of two stiles and two rails, mortised and tenoned, with a panel in
grooves. Along the way it shows the ideas everything else rests on: stock
and parts, named sides, joints that place the parts and cut them, design
dimensions and the cut list.

Write the code into a file, e.g. `door.py`, and run it with
`uv run python door.py` (or `python door.py` with woodwright installed), or
follow along in a notebook to see the model in 3D (see
[Installation](../install.md#viewing-models-in-3d)).

## 1. Stock and parts

```python
import woodwright as ww

oak = ww.Stock.board(thickness=20, species="oak")
```

`Stock` is the material: its thickness and species. Parts are cut from it:
a `Board` has a name, its stock, a length (along the grain) and a width.

Every part belongs to an `Assembly`. The first part added is the *root*,
and `root_location` says where it stands; every other part is placed by
the joints that connect it to the root.

```python
door = ww.Assembly("door", root_location=ww.orient(right_end=ww.UP, back_edge=ww.RIGHT))
stile = door.add(ww.Board("stile_left", oak, length=600, width=60))
rail = door.add(ww.Board("rail_top", oak, length=300, width=60))
```

Each board is imagined lying flat on the bench in front of you: its length
from left to right, its reference face (`top_face`) up, its reference edge
(`front_edge`) towards you. Its six sides are named from there:
`top_face`, `bottom_face`, `front_edge`, `back_edge`, `left_end`,
`right_end`. `orient(right_end=UP, back_edge=RIGHT)` stands the stile up,
its right end at the top, its back edge facing right, where the rails will
be.

## 2. The first joint

```python
door.join(
    ww.MortiseTenon(
        tenon=rail.left_end, mortise=stile.back_edge, position=ww.flush_with(stile.right_end)
    )
)
```

A joint relates two sides: here a tenon on the rail's left end goes into a
mortise in the stile's back edge. That's enough for woodwright to

- **place** the rail: its left end against the stile's back edge, their
  reference faces flush, and along the edge `flush_with(stile.right_end)`:
  the rail's top edge level with the top of the stile (by default it would
  be centered);
- **size** the tenon and mortise from rules of thumb: a tenon a third of
  the stock thick, rounded to a chisel width, shoulders of 5 mm, a mortise
  a bit deeper than the tenon is long;
- **lengthen** the rail by the tenon: its `length` of 300 is its *design
  length*, from shoulder to shoulder, as you'd measure it in the finished
  piece;
- **cut** both parts.

Resolving the assembly works it all out:

```python
model = door.resolve()
print(model.cut_list())
```

```text
stile_left  600 x 60 x 20 mm  oak
            - mortise 50 x 8 mm, 42 deep, in back_edge
rail_top    340 x 60 x 20 mm  oak
            - tenon 50 x 8 mm, 40 long, on left_end
```

Any dimension the rules pick can be given instead, e.g.
`MortiseTenon(..., tenon_thickness=6, tenon_length=30, shoulder=10)`; see
`MortiseTenon` in the [reference](../reference/joints.md) for all of them.

## 3. The whole frame

The other stile and the bottom rail join the same way. The right stile
faces the rail with its front edge, and the bottom rail is flush with the
bottom (left) ends of the stiles:

```python
door = ww.Assembly("door", root_location=ww.orient(right_end=ww.UP, back_edge=ww.RIGHT))
left = door.add(ww.Board("stile_left", oak, length=600, width=60))
right = door.add(ww.Board("stile_right", oak, length=600, width=60))
top = door.add(ww.Board("rail_top", oak, length=300, width=60))
bottom = door.add(ww.Board("rail_bottom", oak, length=300, width=60))

for rail_end, stile_edge, stile_end in [
    (top.left_end, left.back_edge, left.right_end),
    (top.right_end, right.front_edge, right.right_end),
    (bottom.left_end, left.back_edge, left.left_end),
    (bottom.right_end, right.front_edge, right.left_end),
]:
    door.join(
        ww.MortiseTenon(tenon=rail_end, mortise=stile_edge, position=ww.flush_with(stile_end))
    )

print(door.resolve().cut_list())
```

```text
stile  600 x 60 x 20 mm  oak, 2 pieces: stile_left, stile_right
       - 2 x mortise 50 x 8 mm, 42 deep, in back_edge
rail   380 x 60 x 20 mm  oak, 2 pieces: rail_top, rail_bottom
       - tenon 50 x 8 mm, 40 long, on left_end
       - tenon 50 x 8 mm, 40 long, on right_end
```

The right stile is placed through the top rail, and the fourth joint closes
the loop: woodwright checks that it fits (it would report a frame that
doesn't close). Identical parts are listed once: the two stiles are the same
piece, the right one turned over, so its mortises are in what is then its
back edge.

## 4. A panel in grooves

The panel sits in grooves along the inside edges of the frame. Its design
size is the opening of the frame; the grooves add to it. As the grooves
run through the stiles, out at their ends, the tenons are made as thick as
the grooves are wide, with a *haunch* towards the outer edge of the rail
filling the groove:

```python
panel_stock = ww.Stock.board(thickness=10, species="oak")
panel = door.add(ww.Board("panel", panel_stock, length=600 - 2 * 60, width=300))

door.joints.clear()  # redo the corners with haunched tenons
for rail_end, stile_edge, stile_end, outer in [
    (top.left_end, left.back_edge, left.right_end, top.front_edge),
    (top.right_end, right.front_edge, right.right_end, top.front_edge),
    (bottom.left_end, left.back_edge, left.left_end, bottom.back_edge),
    (bottom.right_end, right.front_edge, right.left_end, bottom.back_edge),
]:
    door.join(
        ww.MortiseTenon(
            tenon=rail_end,
            mortise=stile_edge,
            position=ww.flush_with(stile_end),
            tenon_thickness=panel_stock.thickness,
            haunch=outer,
        )
    )
for groove, edge in [
    (left.back_edge, panel.front_edge),
    (right.front_edge, panel.back_edge),
    (top.back_edge, panel.right_end),
    (bottom.front_edge, panel.left_end),
]:
    door.join(ww.GrooveJoint(groove=groove, edge=edge))

print(door.resolve().cut_list())
```

```text
stile  600 x 60 x 20 mm  oak, 2 pieces: stile_left, stile_right
       - 2 x mortise 50 x 10 mm, 42 deep, in back_edge
       - haunch mortise 5 x 10 mm, 10 deep, in back_edge at right_end
       - haunch mortise 5 x 10 mm, 10 deep, in back_edge at left_end
       - groove 10 mm, 10 deep, in back_edge
rail   380 x 60 x 20 mm  oak, 2 pieces: rail_top, rail_bottom
       - haunched tenon 50 x 10 mm, 40 long, haunch 10 long, on left_end
       - haunched tenon 50 x 10 mm, 40 long, haunch 10 long, on right_end
       - groove 10 mm, 10 deep, in back_edge
panel  500 x 320 x 10 mm  oak
```

The panel is placed by its grooves, centered in the frame's thickness, and
cut 20 mm longer and wider than the opening.

## 5. Parameters

To make doors of other sizes, put the design into a function with the
sizes as parameters, as the examples do. The rails' and the panel's lengths
then follow from the outside sizes:

```python
def frame_and_panel_door(
    height: float = 600,
    width: float = 420,
    frame_width: float = 60,
    stock: ww.Stock = oak,
    panel_stock: ww.Stock = panel_stock,
) -> ww.Assembly:
    """A frame of two stiles and two rails, a panel in grooves; outside sizes."""
    door = ww.Assembly("door", root_location=ww.orient(right_end=ww.UP, back_edge=ww.RIGHT))
    rail_length = width - 2 * frame_width
    left = door.add(ww.Board("stile_left", stock, length=height, width=frame_width))
    right = door.add(ww.Board("stile_right", stock, length=height, width=frame_width))
    top = door.add(ww.Board("rail_top", stock, length=rail_length, width=frame_width))
    bottom = door.add(ww.Board("rail_bottom", stock, length=rail_length, width=frame_width))
    panel = door.add(
        ww.Board("panel", panel_stock, length=height - 2 * frame_width, width=rail_length)
    )
    for rail_end, stile_edge, stile_end, outer in [
        (top.left_end, left.back_edge, left.right_end, top.front_edge),
        (top.right_end, right.front_edge, right.right_end, top.front_edge),
        (bottom.left_end, left.back_edge, left.left_end, bottom.back_edge),
        (bottom.right_end, right.front_edge, right.left_end, bottom.back_edge),
    ]:
        door.join(
            ww.MortiseTenon(
                tenon=rail_end,
                mortise=stile_edge,
                position=ww.flush_with(stile_end),
                tenon_thickness=panel_stock.thickness,
                haunch=outer,
            )
        )
    for groove, edge in [
        (left.back_edge, panel.front_edge),
        (right.front_edge, panel.back_edge),
        (top.back_edge, panel.right_end),
        (bottom.front_edge, panel.left_end),
    ]:
        door.join(ww.GrooveJoint(groove=groove, edge=edge))
    return door


tall_door = frame_and_panel_door(height=900, width=450)
```

## 6. Export

From the command line, the file is a design file like any other (see
[Change an example](parameters.md)): the function and `tall_door` are each
exported to their own folder in `output/door/`.

```shell
woodwright export door.py
```

Or from Python, with `export_model`:

```py
from pathlib import Path

from woodwright.export import export_model

tall_door.description = "A tall door with a raised panel."  # for the plans
export_model(tall_door.resolve(), Path("output/tall_door"))
```

This writes the 3D models, the pictures, the shop drawings, the plans PDF
and the cut list (see [Outputs](../guide/outputs.md)); `views=False` leaves
out the slow pictures and drawings.

## Where next

- [How a design is described](../guide/concepts.md): sides, placement,
  positions, design and cut dimensions, rods, mirrored and laminated parts.
- The [example gallery](../gallery/index.md), by joint: find one that does
  what you need and read its code.
- The [reference](../reference/index.md): every joint and cut with its
  options.
