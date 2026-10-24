"""Exporting resolved models: STEP, STL, hidden-line SVG views, shop drawings
and the cut list."""

from pathlib import Path

import build123d as bd

from woodwright.assembly import ResolvedModel
from woodwright.drawing import assembly_sheet, part_sheet, parts_sheet

VIEW_DIRECTION = (1, -1.6, 0.9)  # from the front right, a bit above


def svg_view(
    shape: bd.Shape,
    path: Path,
    direction: tuple[float, float, float] = VIEW_DIRECTION,
    hidden_lines: bool = True,
    line_weight: float = 0.5,
):
    """Hidden-line isometric-ish projection of a shape to SVG, Z up, 1 mm to a unit.

    The hidden lines are dotted, or left out without `hidden_lines`; the
    visible ones `line_weight` mm wide (thicker lines for a small picture).

    project_to_viewport() takes the camera *position* and looks at the shape's
    center, so the camera is placed far away from the center along `direction`.
    """
    center = shape.bounding_box().center()
    camera = center + bd.Vector(direction).normalized() * 5000
    visible, hidden = shape.project_to_viewport(camera, viewport_up=(0, 0, 1))
    svg = bd.ExportSVG(scale=1.0, margin=10)
    if hidden_lines:
        svg.add_layer("hidden", line_color=bd.Color(0.6, 0.6, 0.6), line_type=bd.LineType.ISO_DOT)
        svg.add_shape(hidden, layer="hidden")
    svg.add_layer("visible", line_weight=line_weight)
    svg.add_shape(visible, layer="visible")
    svg.write(str(path))


def exploded(model: ResolvedModel, factor: float = 0.5) -> bd.Compound:
    """The parts moved away from the center of the assembly, `factor` times their distance."""
    shapes = [part.placed_shape for part in model.parts]
    center = bd.Compound(children=[bd.Pos() * s for s in shapes]).bounding_box().center()
    children = []
    for shape in shapes:
        shift = (shape.bounding_box().center() - center) * factor
        moved = bd.Pos(shift) * shape
        moved.label = shape.label
        children.append(moved)
    return bd.Compound(label=f"{model.name}_exploded", children=children)


def export_model(model: ResolvedModel, out_dir: Path, views: bool = True) -> list[Path]:
    """Write the assembly (STEP, STL), each part (STL) and the cut list to `out_dir`.

    With `views`, also hidden-line SVG views of the assembly, its exploded
    view and each part in its own frame, and shop drawings in `drawings/`:
    a dimensioned sheet per part (one per group of identical parts) and, for
    more than one part, the assembly and its parts (see `woodwright.drawing`).
    """

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    def out(name: str) -> Path:
        path = out_dir / name
        written.append(path)
        return path

    assembled = model.compound()
    bd.export_step(assembled, str(out("assembled.step")))
    bd.export_stl(assembled, str(out("assembled.stl")), tolerance=0.01)
    if views:
        svg_view(assembled, out("assembled.svg"))
        if len(model.parts) > 1:
            svg_view(exploded(model), out("exploded.svg"))
    for part in model.parts:
        bd.export_stl(part.shape, str(out(f"{part.part.name}.stl")), tolerance=0.01)
        if views:
            svg_view(part.shape, out(f"{part.part.name}.svg"))
    if views:
        (out_dir / "drawings").mkdir(exist_ok=True)
        if len(model.parts) > 1:
            assembly_sheet(model).write(out("drawings/assembly.svg"))
            parts_sheet(model).write(out("drawings/parts.svg"))
        for group in model.groups:
            part_sheet(model, group.first).write(out(f"drawings/{group.name}.svg"))
    out("cut_list.txt").write_text(model.cut_list() + "\n")
    return written
