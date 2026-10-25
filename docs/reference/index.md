# Reference

The API, generated from the docstrings in the source. Everything you need
for a design is importable from the package itself:

```python
import woodwright as ww

oak = ww.Stock.board(thickness=20, species="oak")
frame = ww.Assembly("corner", root_location=ww.orient(right_end=ww.UP, back_edge=ww.RIGHT))
```

- [Command line](cli.md): `woodwright list` and `woodwright export`.
- [Assemblies](assembly.md): `Assembly`, resolving it into a `ResolvedModel`, the cut list.
- [Parts and stock](part.md): `Stock`, `Board`, `Rod` and their named sides.
- [Placement](placement.md): orienting the first part, positions along and across a joint.
- [Joints](joints.md): every joint, from `Butt` to `BlindMitredDovetail`.
- [Cuts](cuts.md): cuts made by joints, or added to a part yourself.
- [Rules](rules.md): rules of thumb for the dimensions you leave out.
- [Export](export.md): writing the model, its views, drawings and plans.
- [Drawings and plans](drawing.md): shop drawings, sheets, the plans PDF,
  identical parts.

The examples are in `woodwright.examples` (see the [gallery](../gallery/index.md)).
woodwright is built on [build123d](https://build123d.readthedocs.io/): the
shapes it produces are build123d shapes.

!!! note "Early alpha"

    The API will still change between versions.
