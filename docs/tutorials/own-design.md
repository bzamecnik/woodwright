# From an example to your own design

When changing an example's [parameters](parameters.md) isn't enough, copy
its code into your design file and change the code. This page takes the
picture frame, mitred at its corners, and turns it into a frame with a
walnut key across each corner.

It's Python, but you only need to follow the pattern of the code you
copied. An AI coding assistant (e.g. Claude Code) can help with the
changes, too.

## 1. Find the example's code

Each example's page in the [gallery](../gallery/index.md) shows its code.
This is [projects.picture_frame](../gallery/projects/picture_frame/index.md):

```py
def picture_frame(
    width: float = 400,
    height: float = 300,
    member_width: float = 40,
    stock: Stock = OAK,
) -> Assembly:
    """A frame mitred at all four corners; outside sizes."""
    asm = Assembly("picture_frame", root_location=STANDING)
    left = asm.add(Board("left", stock, length=height, width=member_width))
    top = asm.add(Board("top", stock, length=width, width=member_width))
    right = asm.add(Board("right", stock, length=height, width=member_width))
    bottom = asm.add(Board("bottom", stock, length=width, width=member_width))
    members = [left, top, right, bottom]
    for a, b in zip(members, members[1:] + members[:1], strict=True):
        asm.join(MitreCorner(a.right_end, b.left_end, a.back_edge, b.back_edge))
    return asm
```

Reading it: an `Assembly` named `picture_frame`, four boards added to it
(`asm.add`), and a `MitreCorner` joint between each board and the next
(`asm.join`): the right end of one meets the left end of the next, mitred
with their back edges inside. The boards' lengths are the outside sizes.

## 2. Copy it with what it uses

Copy the function into your file, `my_frame.py`. The examples share a few
names defined elsewhere in the library, here `OAK` (the stock) and
`STANDING` (which way the first board stands). Define them in your file
instead, and import the rest from `woodwright`:

```python
from woodwright import RIGHT, UP, Assembly, Board, MitreCorner, Stock, orient

OAK = Stock.board(thickness=20, species="oak")
STANDING = orient(right_end=UP, back_edge=RIGHT)  # the first board stands up


def picture_frame(
    width: float = 400,
    height: float = 300,
    member_width: float = 40,
    stock: Stock = OAK,
) -> Assembly:
    """A frame mitred at all four corners; outside sizes."""
    asm = Assembly("picture_frame", root_location=STANDING)
    left = asm.add(Board("left", stock, length=height, width=member_width))
    top = asm.add(Board("top", stock, length=width, width=member_width))
    right = asm.add(Board("right", stock, length=height, width=member_width))
    bottom = asm.add(Board("bottom", stock, length=width, width=member_width))
    members = [left, top, right, bottom]
    for a, b in zip(members, members[1:] + members[:1], strict=True):
        asm.join(MitreCorner(a.right_end, b.left_end, a.back_edge, b.back_edge))
    return asm
```

Everything an example uses can be imported from `woodwright`: parts
(`Board`, `Rod`), `Stock`, every joint and cut, and the directions and
helpers for placing parts (`UP`, `orient`, `flush_with`...). The shared
stock and orientations of the examples are in
[`examples/_common.py`](https://github.com/bzamecnik/woodwright/blob/HEAD/src/woodwright/examples/_common.py).

Check that it exports as before:

```shell
woodwright export my_frame.py
```

A function is exported like a design assigned to a name when it returns an
assembly (`-> Assembly`) and all its parameters have defaults: to
`output/my_frame/picture_frame`.

## 3. Change it

Now the change: a key across each outside corner, a thin walnut offcut glued
into a saw kerf. In the [gallery](../gallery/index.md), the
[keyed mitre corner](../gallery/joints/keyed_mitre_corner/index.md) shows the
joint for one corner: `KeyedMitre`, which takes the same sides as
`MitreCorner` and the keys, boards added to the assembly like the others.

```python
from woodwright import RIGHT, UP, Assembly, Board, KeyedMitre, Stock, orient

OAK = Stock.board(thickness=20, species="oak")
WALNUT = Stock.board(thickness=3, species="walnut")  # for the keys
STANDING = orient(right_end=UP, back_edge=RIGHT)


def keyed_picture_frame(
    width: float = 400,
    height: float = 300,
    member_width: float = 40,
    stock: Stock = OAK,
) -> Assembly:
    """A frame mitred at all four corners, a walnut key across each; outside sizes."""
    asm = Assembly("keyed_picture_frame", root_location=STANDING)
    left = asm.add(Board("left", stock, length=height, width=member_width))
    top = asm.add(Board("top", stock, length=width, width=member_width))
    right = asm.add(Board("right", stock, length=height, width=member_width))
    bottom = asm.add(Board("bottom", stock, length=width, width=member_width))
    members = [left, top, right, bottom]
    for i, (a, b) in enumerate(zip(members, members[1:] + members[:1], strict=True)):
        key = asm.add(Board(f"key_{i + 1}", WALNUT, length=50, width=20))
        asm.join(KeyedMitre(a.right_end, b.left_end, a.back_edge, b.back_edge, keys=(key,)))
    return asm
```

The kerfs, their depth and where they lie, and the keys trimmed to
triangles are worked out by the joint. The cut list:

```text
left_right  300 x 40 x 20 mm  oak, 2 pieces: left, right
            - mitre 45 deg on right_end, back_edge inside
            - key kerf 3 mm wide, 19 deep across the corner with top, 10 from top_face
            - mitre 45 deg on left_end, back_edge inside
            - key kerf 3 mm wide, 19 deep across the corner with bottom, 10 from top_face
top_bottom  400 x 40 x 20 mm  oak, 2 pieces: top, bottom
            - ...
key         50 x 20 x 3 mm  walnut, 4 pieces: key_1, key_2, key_3, key_4
            - trimmed flush with left and top, to a triangle
```

Identical parts are listed once, with their count.

## 4. Use it

The function is your own design now, with its own parameters:

```python
small = keyed_picture_frame(width=240, height=180, member_width=30)
```

```shell
woodwright export my_frame.py:small
```

## Tips

- Every joint's options are in the [reference](../reference/joints.md),
  e.g. the number of keys, their depth and angle, or dovetail keys.
- Names of sides (`right_end`, `back_edge`, `top_face`...) and how parts
  are placed by joints are explained in
  [How a design is described](../guide/concepts.md).
- To start with an empty file instead, see
  [A design from scratch](from-scratch.md).
