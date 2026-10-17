"""Simple blind mortise-and-tenon T-joint of two perpendicular boards.

The rail is tenoned into the back edge of the stile, centered along it, with
their reference faces flush. The joint derives the tenon and the mortise, the
rail's cut length and its placement; the user only gives design dimensions.

The stile stands up (X to the right, Y to the back, Z up), its back edge
facing right.
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

OUT_DIR = Path(__file__).resolve().parent.parent / "output" / "mortise_tenon"

# --- Design -----------------------------------------------------------------

oak = ww.Stock.board(thickness=20, species="oak")

frame = ww.Assembly("mortise_tenon", root_location=ww.orient(right_end=ww.UP, back_edge=ww.RIGHT))
stile = frame.add(ww.Board("stile", oak, length=600, width=60))
rail = frame.add(ww.Board("rail", oak, length=300, width=60))  # shoulder to shoulder
frame.join(
    ww.MortiseTenon(
        tenon=rail.left_end,
        mortise=stile.back_edge,
        # tenon_thickness=10,  # overrides the default (a third of the stock, as a chisel)
    )
)

model = frame.resolve()

stile_shape = model[stile].placed_shape
rail_shape = model[rail].placed_shape
stile_shape.color = Color(0.85, 0.65, 0.40)
rail_shape.color = Color(0.70, 0.45, 0.25)

# --- Checks (what the validator will do) ------------------------------------

overlap = stile_shape.intersect(rail_shape)
overlap_volume = overlap.volume if overlap is not None else 0.0
assert overlap_volume < 1e-6, f"parts interfere: {overlap_volume:.3f} mm^3"

# --- Export -----------------------------------------------------------------


def export_view(shape, path: Path, direction=(1, -1.6, 0.9)):
    """Hidden-line isometric-ish projection to SVG.

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
        label="mortise_tenon", children=[Pos(0, 0, 0) * stile_shape, Pos(0, 0, 0) * rail_shape]
    )
    # Pull the rail out along X so the tenon and mortise are visible.
    exploded = Compound(
        label="mortise_tenon_exploded",
        children=[Pos(0, 0, 0) * stile_shape, Pos(80, 0, 0) * rail_shape],
    )

    for name, shape in [
        ("assembled", assembled),
        ("exploded", exploded),
        ("stile", stile_shape),
        ("rail", rail_shape),
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
