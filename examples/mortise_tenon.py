"""Simple blind mortise-and-tenon T-joint of two perpendicular boards.

Plain build123d, no woodworking abstractions yet: this is the "base layer"
experiment to see what the semantic layer will later have to generate.

Coordinates (global frame, mm):
  X = width (to the right), Y = depth (away from viewer), Z = up.

  stile: vertical board, L along Z, W along X, T along Y
  rail:  horizontal board, L along X, W along Z, T along Y,
         tenoned into the right edge of the stile, centered on its length
         and flush with it on both faces.
"""

from pathlib import Path

from build123d import (
    Align,
    Box,
    Color,
    Compound,
    ExportSVG,
    LineType,
    Pos,
    Vector,
    export_step,
    export_stl,
)

OUT_DIR = Path(__file__).resolve().parent.parent / "output" / "mortise_tenon"

MIN = (Align.MIN, Align.MIN, Align.MIN)

# --- Design parameters (what the user would decide) -------------------------

stock_t = 20.0  # thickness of both boards

stile_length = 600.0
stile_width = 60.0

rail_shoulder_length = 300.0  # visible length, from stile edge to rail end
rail_width = 60.0

# --- Joint parameters (what the joint library would derive by default) ------

tenon_thickness = 8.0  # ~1/3 of stock, rounded to a common chisel size
tenon_shoulder = 5.0  # top/bottom shoulders on the rail's edges
tenon_length = 40.0  # 2/3 of stile width
mortise_clearance = 2.0  # extra depth at the bottom of the mortise for glue

# --- Derived values (what the resolver would compute) -----------------------

tenon_width = rail_width - 2 * tenon_shoulder
mortise_depth = tenon_length + mortise_clearance
rail_cut_length = rail_shoulder_length + tenon_length  # length of stock to cut

# Rail sits in the middle of the stile's length, faces flush with the stile.
rail_z = (stile_length - rail_width) / 2
cheek_y = (stock_t - tenon_thickness) / 2  # tenon centered in thickness

# --- Geometry ---------------------------------------------------------------

# Stile: blank board minus the mortise cut into its right edge (x = stile_width).
stile_blank = Box(stile_width, stock_t, stile_length, align=MIN)
mortise = Pos(stile_width - mortise_depth, cheek_y, rail_z + tenon_shoulder) * Box(
    mortise_depth, tenon_thickness, tenon_width, align=MIN
)
stile = stile_blank - mortise

# Rail: body from the stile edge outward, plus the tenon reaching into the stile.
rail_body = Pos(stile_width, 0, rail_z) * Box(rail_shoulder_length, stock_t, rail_width, align=MIN)
tenon = Pos(stile_width - tenon_length, cheek_y, rail_z + tenon_shoulder) * Box(
    tenon_length, tenon_thickness, tenon_width, align=MIN
)
rail = rail_body + tenon

stile.label, stile.color = "stile", Color(0.85, 0.65, 0.40)
rail.label, rail.color = "rail", Color(0.70, 0.45, 0.25)

# --- Checks (what the validator would do) -----------------------------------

overlap = stile.intersect(rail)
overlap_volume = overlap.volume if overlap is not None else 0.0
assert overlap_volume < 1e-6, f"parts interfere: {overlap_volume:.3f} mm^3"

expected_rail_volume = (
    rail_shoulder_length * rail_width * stock_t + tenon_length * tenon_width * tenon_thickness
)
assert abs(rail.volume - expected_rail_volume) < 1e-6

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
    svg.add_layer("hidden", line_color=(160, 160, 160), line_type=LineType.ISO_DOT)
    svg.add_layer("visible", line_weight=0.5)
    svg.add_shape(hidden, layer="hidden")
    svg.add_shape(visible, layer="visible")
    svg.write(str(path))


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # A shape can have only one parent Compound (build123d assemblies are
    # trees), so each assembly gets its own placed copies (Pos(...) * shape).
    assembled = Compound(
        label="mortise_tenon", children=[Pos(0, 0, 0) * stile, Pos(0, 0, 0) * rail]
    )
    # Pull the rail out along X so the tenon and mortise are visible.
    exploded = Compound(
        label="mortise_tenon_exploded",
        children=[Pos(0, 0, 0) * stile, Pos(80, 0, 0) * rail],
    )

    for name, shape in [
        ("assembled", assembled),
        ("exploded", exploded),
        ("stile", stile),
        ("rail", rail),
    ]:
        export_stl(shape, str(OUT_DIR / f"{name}.stl"), tolerance=0.01)
        export_view(shape, OUT_DIR / f"{name}.svg")
    export_step(assembled, str(OUT_DIR / "assembled.step"))

    print("Cut list:")
    print(f"  stile  1x  {stile_length:.0f} x {stile_width:.0f} x {stock_t:.0f} mm")
    print(f"  rail   1x  {rail_cut_length:.0f} x {rail_width:.0f} x {stock_t:.0f} mm")
    print("Joinery:")
    print(
        f"  mortise {tenon_width:.0f} x {tenon_thickness:.0f} mm, "
        f"{mortise_depth:.0f} deep, in stile right edge"
    )
    print(
        f"  tenon   {tenon_width:.0f} x {tenon_thickness:.0f} mm, "
        f"{tenon_length:.0f} long, on rail left end"
    )
    print(f"Interference: {overlap_volume:.3f} mm^3")
    print(f"Wrote files to {OUT_DIR}")


if __name__ == "__main__":
    main()
