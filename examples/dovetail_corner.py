"""Through-dovetail corner of a carcase: a top board joined to a side board.

Plain build123d, no woodworking abstractions yet: like mortise_tenon.py, this
is a "base layer" experiment to see what the semantic layer will later have to
generate.

Coordinates (global frame, mm):
  X = width (to the right), Y = depth (away from viewer), Z = up.

  side: vertical board at the left of the case, H along Z, D along Y,
        T along X (outer face at x = 0, inner face at x = T)
  top:  horizontal board, L along X, D along Y, T along Z
        (top face at z = H, flush with the top end of the side)

The two boards overlap in the corner block x in [0, T], z in [H - T, H].
Tails are cut on the top board, pins on the side board. Seen from above, both
are trapezoids in the XY plane, extruded through the top's thickness (Z):
tails flare towards the top's end (x = 0), so the top can only be lifted off
upwards (+Z), and the side cannot be pulled outwards (-X).

Along the depth (Y) the joint is laid out as:
  half pin | tail | pin | tail | ... | pin | tail | half pin
"""

from pathlib import Path

from build123d import (
    Align,
    Box,
    Color,
    Compound,
    ExportSVG,
    LineType,
    Polygon,
    Pos,
    Solid,
    Vector,
    export_step,
    export_stl,
    extrude,
)

OUT_DIR = Path(__file__).resolve().parent.parent / "output" / "dovetail_corner"

MIN = (Align.MIN, Align.MIN, Align.MIN)

# --- Design parameters (what the user would decide) -------------------------

stock_t = 20.0  # thickness of both boards
depth = 200.0  # depth of the case = width of both boards

side_height = 400.0
top_length = 500.0

# --- Joint parameters (what the joint library would derive by default) ------

tail_count = 4
slope_ratio = 7.0  # 1:7, between 1:6 (softwood) and 1:8 (hardwood)
pin_width = 8.0  # narrowest width of a pin, on the side's outer face (x = 0)
half_pin_width = 10.0  # narrowest width of the half pins at the board edges

# --- Derived values (what the resolver would compute) -----------------------

# How far each sloped flank leans over the full thickness of the joint.
flare = stock_t / slope_ratio

# At x = 0 the pins are narrowest and the tails widest.
tail_wide = (depth - 2 * half_pin_width - (tail_count - 1) * pin_width) / tail_count
tail_narrow = tail_wide - 2 * flare
assert tail_narrow > 0, "tails too narrow for this slope and pin width"

joint_z = side_height - stock_t  # bottom of the corner block (underside of top)


def pin_profiles() -> list[list[tuple[float, float]]]:
    """XY outlines of the pins (incl. half pins) in the corner block.

    Each outline is (y at x = 0, y at x = T) for both flanks of the pin:
    narrow at the outer face x = 0, wide at the inner face x = T.
    """
    t = stock_t
    profiles = []

    # Half pin at the front edge (y = 0): only its back flank is sloped.
    y = half_pin_width
    profiles.append([(0, 0), (t, 0), (t, y + flare), (0, y)])

    # Full pins between tails.
    for _ in range(tail_count - 1):
        y0 = y + tail_wide  # front flank of the pin at x = 0
        y1 = y0 + pin_width  # back flank of the pin at x = 0
        profiles.append([(0, y0), (t, y0 - flare), (t, y1 + flare), (0, y1)])
        y = y1

    # Half pin at the back edge (y = depth).
    y0 = y + tail_wide
    assert abs(depth - y0 - half_pin_width) < 1e-9
    profiles.append([(0, y0), (t, y0 - flare), (t, depth), (0, depth)])
    return profiles


# --- Geometry ---------------------------------------------------------------

side_blank = Box(stock_t, depth, side_height, align=MIN)
top_blank = Pos(0, 0, joint_z) * Box(top_length, depth, stock_t, align=MIN)
corner = Pos(0, 0, joint_z) * Box(stock_t, depth, stock_t, align=MIN)

# Pins: trapezoidal prisms through the whole corner block, extruded along Z.
pin_solids = [
    extrude(Pos(0, 0, joint_z) * Polygon(*pts), amount=stock_t)
    for pts in pin_profiles()
]
pins = Solid.fuse(*pin_solids) if len(pin_solids) > 1 else pin_solids[0]
# Tails: whatever of the corner block is not a pin.
tails = corner - pins

# Each board keeps its own part of the corner block.
side = side_blank - tails
top = top_blank - pins

side.label, side.color = "side", Color(0.85, 0.65, 0.40)
top.label, top.color = "top", Color(0.70, 0.45, 0.25)

# --- Checks (what the validator would do) -----------------------------------

overlap = side.intersect(top)
overlap_volume = overlap.volume if overlap is not None else 0.0
assert overlap_volume < 1e-6, f"parts interfere: {overlap_volume:.3f} mm^3"

# Pins + tails fill the corner block exactly: no gaps in the joint.
expected_volume = side_blank.volume + top_blank.volume - corner.volume
assert abs(side.volume + top.volume - expected_volume) < 1e-6

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
        label="dovetail_corner", children=[Pos(0, 0, 0) * side, Pos(0, 0, 0) * top]
    )
    # Lift the top up along Z, the only direction the tails can come out.
    exploded = Compound(
        label="dovetail_corner_exploded",
        children=[Pos(0, 0, 0) * side, Pos(0, 0, 60) * top],
    )

    for name, shape in [
        ("assembled", assembled),
        ("exploded", exploded),
        ("side", side),
        ("top", top),
    ]:
        export_stl(shape, str(OUT_DIR / f"{name}.stl"), tolerance=0.01)
        export_view(shape, OUT_DIR / f"{name}.svg")
    export_step(assembled, str(OUT_DIR / "assembled.step"))

    print("Cut list:")
    print(f"  side  1x  {side_height:.0f} x {depth:.0f} x {stock_t:.0f} mm")
    print(f"  top   1x  {top_length:.0f} x {depth:.0f} x {stock_t:.0f} mm")
    print("Joinery (through dovetails, slope 1:{:.0f}):".format(slope_ratio))
    print(
        f"  tails  {tail_count}x on top left end, "
        f"{tail_wide:.1f} -> {tail_narrow:.1f} mm wide, {stock_t:.0f} long"
    )
    print(
        f"  pins   {tail_count - 1}x + 2 half pins on side top end, "
        f"{pin_width:.1f} -> {pin_width + 2 * flare:.1f} mm wide "
        f"(half pins {half_pin_width:.1f} -> {half_pin_width + flare:.1f} mm)"
    )
    print(f"Interference: {overlap_volume:.3f} mm^3")
    print(f"Wrote files to {OUT_DIR}")


if __name__ == "__main__":
    main()
