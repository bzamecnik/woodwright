"""Through-dovetail corner of a carcase: a top board joined to a side board.

Tails are cut on the left end of the top, pins on the top (right) end of the
side. Both boards reach through each other, so their design lengths are the
outside dimensions minus the other board's thickness; the joint adds that
back as an allowance. The geometry of pins and tails is built once in the
side's frame and split between the two boards, so they fit by construction.

The side stands up (X to the right, Y to the back, Z up), its reference
face outside, to the left, at x = 0. The tails flare
towards the top's end, so the top can only be lifted off upwards (+Z).
"""

from pathlib import Path

from build123d import (
    Color,
    Compound,
    ExportSVG,
    LineType,
    Pos,
    Vector,
    export_step,
    export_stl,
)

import woodwright as ww

OUT_DIR = Path(__file__).resolve().parent.parent / "output" / "dovetail_corner"

# --- Design -----------------------------------------------------------------

pine = ww.Stock.board(thickness=20, species="pine")
depth = 200.0  # depth of the case = width of both boards
side_height = 400.0  # outside dimensions
top_length = 500.0

carcase = ww.Assembly("dovetail_corner", root_location=ww.orient(right_end=ww.UP, ref_face=ww.LEFT))
side = carcase.add(ww.Board("side", pine, length=side_height - pine.thickness, width=depth))
top = carcase.add(ww.Board("top", pine, length=top_length - pine.thickness, width=depth))
carcase.join(ww.ThroughDovetail(tails=top.left_end, pins=side.right_end, tail_count=4))

model = carcase.resolve()

side_shape = model[side].placed_shape
top_shape = model[top].placed_shape
side_shape.color = Color(0.85, 0.65, 0.40)
top_shape.color = Color(0.70, 0.45, 0.25)

# --- Checks (what the validator will do) ------------------------------------

overlap = side_shape.intersect(top_shape)
overlap_volume = overlap.volume if overlap is not None else 0.0
assert overlap_volume < 1e-6, f"parts interfere: {overlap_volume:.3f} mm^3"

# Pins + tails fill the corner block exactly: no gaps in the joint.
blank_volume = sum(
    resolved.size[0] * resolved.size[1] * resolved.size[2] for resolved in model.parts
)
corner_volume = pine.thickness**2 * depth
assert abs(side_shape.volume + top_shape.volume - (blank_volume - corner_volume)) < 1e-6

# --- Export -----------------------------------------------------------------


def export_view(shape, path: Path, direction=(-1, -1.6, 0.9)):
    """Hidden-line isometric-ish projection to SVG, from the outer-left side.

    project_to_viewport() takes the camera *position* and looks at the shape's
    center, so place the camera far away from the center along `direction`.
    """
    center = shape.bounding_box().center()
    camera = center + Vector(direction).normalized() * 5000
    visible, hidden = shape.project_to_viewport(camera, viewport_up=(0, 0, 1))
    svg = ExportSVG(scale=1.0, margin=10)
    svg.add_layer("hidden", line_color=(0.6, 0.6, 0.6), line_type=LineType.ISO_DOT)
    svg.add_layer("visible", line_weight=0.5)
    svg.add_shape(hidden, layer="hidden")
    svg.add_shape(visible, layer="visible")
    svg.write(str(path))


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # A shape can have only one parent Compound (build123d assemblies are
    # trees), so each assembly gets its own placed copies (Pos(...) * shape).
    assembled = Compound(
        label="dovetail_corner", children=[Pos(0, 0, 0) * side_shape, Pos(0, 0, 0) * top_shape]
    )
    # Lift the top up along Z, the only direction the tails can come out.
    exploded = Compound(
        label="dovetail_corner_exploded",
        children=[Pos(0, 0, 0) * side_shape, Pos(0, 0, 60) * top_shape],
    )

    for name, shape in [
        ("assembled", assembled),
        ("exploded", exploded),
        ("side", side_shape),
        ("top", top_shape),
    ]:
        export_stl(shape, str(OUT_DIR / f"{name}.stl"), tolerance=0.01)
        export_view(shape, OUT_DIR / f"{name}.svg")
    export_step(assembled, str(OUT_DIR / "assembled.step"))

    print("Cut list:")
    print(model.cut_list())
    print(f"Interference: {overlap_volume:.3f} mm^3")
    print(f"Wrote files to {OUT_DIR}")


if __name__ == "__main__":
    main()
