# Change an example

Every example is made to measure: its sizes, stock thicknesses and some of
its joinery are parameters with default values. You change them in a small
text file, a *design file*, and export that instead of the example.

## What can be changed

Each example's page in the [gallery](../gallery/index.md) lists its
parameters with their defaults, e.g. the
[cabinet door](../gallery/projects/cabinet_door/index.md):

| Parameter | Default |
| --- | --- |
| `height` | `600` |
| `width` | `400` |
| `member_width` | `30` |
| `mitre_depth` | `10` |
| ... | |

Sizes are in millimetres. The description below the pictures says what they
mean, e.g. whether they are outside sizes. They are also at the top of the
example's code in
[the example library](https://github.com/bzamecnik/woodwright/tree/HEAD/src/woodwright/examples).

## A design file

In a plain text editor (TextEdit set to plain text, Notepad, VS Code...)
write a file `my_door.py` with the sizes you want:

```python
from woodwright.examples import projects

door = projects.cabinet_door(height=700, width=450)
```

and export it, in the folder where you saved it:

```shell
woodwright export my_door.py
```

The results are in `output/my_door/door`: the folder is named after the
file, and the subfolder after the name you gave the design (`door`).
Parameters you leave out keep their defaults. Write numbers without units
(`700`, not `700mm`); decimals with a dot (`22.5`).

## Several designs in one file

Every design assigned to a name is exported, each to its own folder:

```python
from woodwright.examples import projects

small_door = projects.cabinet_door(height=500, width=350)
large_door = projects.cabinet_door(height=900, width=450, member_width=40)
```

To export only one of them, add its name after a colon:

```shell
woodwright export my_door.py:large_door
```

## Other stock

The thickness and species of the wood come from a `Stock` parameter
(`stock`, and e.g. `panel_stock` for a panel). Make your own:

```python
from woodwright import Stock
from woodwright.examples import projects

walnut = Stock.board(thickness=22, species="walnut")
door = projects.cabinet_door(height=700, width=450, stock=walnut)
```

Round stock (dowels, rods, round legs) is `Stock.rod(diameter=25, species="ash")`.

## A description for the plans

The plans PDF can describe your piece on a page after the contents: the
wood, the finish, the order of work. Add a text to the design:

```python
door.description = """
    A glazed door for a wall cabinet.

    - **Wood**: walnut, planed all round.
    - Fit the glass after the finish.
    """
```

Headings start with `#`, list items with `-` or `1.`, `**bold**` and
`*italic*` work as in Markdown.

## When it doesn't fit

woodwright doesn't check yet whether the sizes make sense together: a door
only a little wider than its two stiles still exports, with panels 2 mm
wide. Look at the pictures and the drawings before you cut.

When the parameters aren't enough, e.g. you want a third rail or another
joint at the corners, the next step is to
[copy the example's code](own-design.md) into your file and change it.
