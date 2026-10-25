# How a design is described

A woodwright design says what a woodworker would say about a piece: which
boards it is made of, and how they are joined. It doesn't say where each
board is in space or how big each tenon is: those follow from the joints.
This page goes through the ideas one by one; the
[reference](../reference/index.md) has every option.

```python
import woodwright as ww
```

## Stock

`Stock` is the material parts are cut from: a thickness in millimetres and
a species, for the cut list.

```python
oak = ww.Stock.board(thickness=20, species="oak")
dowel_stock = ww.Stock.rod(diameter=10, species="beech")  # round stock
```

## Parts and their sides

A `Board` is a named piece of board stock with a length (along the grain)
and a width. Picture it lying flat on the bench in front of you, its length
from left to right, its reference face up and its reference edge towards
you. Its six sides are named from there:

| Side | Where | Also |
| --- | --- | --- |
| `top_face` | facing up | `ref_face` |
| `bottom_face` | facing down | |
| `front_edge` | towards you | `ref_edge` |
| `back_edge` | away from you | |
| `left_end` | to the left | |
| `right_end` | to the right | |

Joints and cuts refer to these sides, e.g. `rail.left_end` or
`stile.back_edge`. Where two sides meet is an arris: `board.arris(board.top_face,
board.front_edge)`, the reference arris.

```python
shelf = ww.Board("shelf", oak, length=500, width=200)
shelf.right_end, shelf.ref_face
```

A `Rod` is a part of round stock: a dowel, a peg, a rung, a round leg. It
has the same six side names, thought of as the sides of the square box
around it; only its ends are real, the others are directions (e.g. for a
hole across it or a flat on it).

```python
rung = ww.Rod("rung", ww.Stock.rod(diameter=25, species="ash"), length=400)
```

A board can be **mirrored** (`mirror=True`): the mirror image of the same
board, e.g. the right side of a case against the left one, both with their
reference faces outside and their reference edges at the front. Its ends
swap names, so the same joints on the same named sides make the mirror
image. A board can also be **laminated** (`plies=2`): glued up from equal
boards, through its thickness or across its width; the glue lines show in
the drawings and the cut list.

## Design dimensions

The lengths you give are *design dimensions*: what you'd measure in the
finished piece, between the joints. A rail is 300 mm from shoulder to
shoulder; its tenons are added to its cut length. A panel's size is the
opening of its frame; the grooves add to it. The cut list gives the cut
sizes.

## The assembly

An `Assembly` holds the parts and the joints between them. The first part
added is the *root*: `root_location` says which way it stands, by the
directions two of its sides face. Every other part is placed by joints,
directly or through other parts.

```python
leg_stock = ww.Stock.board(thickness=60, species="oak")
table = ww.Assembly("table", root_location=ww.orient(right_end=ww.UP, back_edge=ww.RIGHT))
leg = table.add(ww.Board("leg", leg_stock, length=720, width=60))
```

Directions are as seen by someone in front of the piece: `RIGHT`, `LEFT`,
`BACK` (away from the viewer), `FRONT`, `UP`, `DOWN`. Here the leg stands
up (its right end up) with its back edge to the right.

## Joints

A joint relates a side of one part to a side of another. It does three
things:

1. **places** the second part against the first (the side of one against
   the side of the other, two other sides flush);
2. **sizes** itself, filling in what you didn't give from rules of thumb
   (a tenon about a third of the stock thick, rounded to a chisel width;
   see [Rules](../reference/rules.md)) and lengthening parts where needed;
3. **cuts** both parts: the tenon and the mortise, a groove, a dado, the
   tails and pins.

```python
apron = table.add(ww.Board("apron", oak, length=500, width=100))
table.join(
    ww.MortiseTenon(
        tenon=apron.left_end,
        mortise=leg.back_edge,
        position=ww.flush_with(leg.right_end),
        shoulder=(10, 15),
    )
)
print(table.resolve().cut_list())
```

```text
leg    720 x 60 x 60 mm  oak
       - mortise 75 x 8 mm, 42 deep, in back_edge
apron  540 x 100 x 20 mm  oak
       - tenon 75 x 8 mm, 40 long, on left_end
```

Every joint has its own sides with their own names (`tenon=`, `mortise=`;
`dado=`, `end=`; `groove=`, `edge=` ...), and most have a `position`.

### Positions

By default, the parts meet with their reference faces flush (across the
joint) and centered on each other (along it). Along the joint, `position`
sets that otherwise:

- `ww.flush_with(leg.right_end)`: flush with the end of the leg, e.g. an
  apron level with the top of the leg;
- `ww.offset(100, leg.right_end)`: 100 mm in from it;
- `ww.centered()`: centered (the default for most joints).

Across it, `across` sets the second part back from the flush faces
(`across=ww.offset(5)`), or centers it in the thickness
(`across=ww.centered()`), and `flush` chooses which sides are flush
instead of the reference faces.

### Placing joints and the others

Joints that put one part against another place it. Some don't: a `Screw`
or a `Bore` through two parts already placed, a `Butterfly` key across two
boards. They cut the parts where the placing joints put them. If a part
isn't reached by placing joints from the root, resolving says which.

A loop, like the four corners of a frame, is checked: the last joint must
agree with where the others put the parts, or resolving says by how much it
is off.

### Separate pieces

Some joints have pieces of their own: the loose tenon of `LooseTenon`, the
keys of `KeyedMitre`, the dowels of `Dowels`. They are parts you make and
add to the assembly like the others, and give to the joint, which places
and cuts them.

## Cuts

The cuts joints make come by themselves. Cuts that don't belong to a joint
are added to a part: chamfers, holes, tapers, end chamfers, mitres.

```python
shelf = ww.Board("shelf", oak, length=500, width=200)
shelf.cut(ww.Chamfer(shelf.arris(shelf.top_face, shelf.front_edge), size=3))
shelf.cut(ww.Hole(shelf.top_face, 8, depth=12, at={shelf.left_end: 50}))
```

## Resolving

`assembly.resolve()` works out the design: it fills in the joints'
defaults, sizes the blanks, places every part and collects their cuts. It
returns a `ResolvedModel` and leaves the design unchanged, so you can
change a parameter and resolve again.

From the resolved model:

- `model.cut_list()`: the cut list, identical parts once;
- `model.parts`: each part with its size, cuts, location and 3D shape;
- `model.compound()`: the whole assembly as a build123d shape;
- `export_model(model, path)`: all the files (see [Outputs](outputs.md)).

## Identical parts

Parts that are the same piece, perhaps turned over (end for end, face
down), are found and grouped: "2 pieces: stile_left, stile_right" in the
cut list, one drawing for both. Mirror images are grouped too, marked as
such. You don't have to declare them; name the parts as they are in the
piece.
