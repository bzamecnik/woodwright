"""Shop drawings: dimensioned orthographic views of parts and assemblies.

A part sheet shows the part lying on the bench as in its frame (reference
face up, reference edge towards the woodworker) in third-angle projection,
folded around the top face and the front edge, each view labelled with the
side it shows. Its overall (cut) dimensions are given outermost. See
docs/plan.md, M10, for the conventions.

Views are hidden-line projections along the axes of the part frame (or of
the assembly), so a model coordinate maps directly to a drawing coordinate.
Everything is laid out in paper millimetres on a `Sheet` at a standard
scale chosen to fit an A4 sheet.
"""

import math
from dataclasses import dataclass, field, replace
from itertools import pairwise

import build123d as bd

from woodwright.assembly import ResolvedModel, ResolvedPart
from woodwright.part import Rod, Side, SideRef
from woodwright.sheet import TEXT, TICK, Point2, Sheet, text_width

Vec3 = tuple[float, float, float]
Polyline = list[Point2]

# the ISO 5455 scales and the in-between ones common in woodworking plans
SCALES = [2, 1, 1 / 2, 1 / 2.5, 1 / 4, 1 / 5, 1 / 8, 1 / 10, 1 / 15, 1 / 20, 1 / 25, 1 / 50]
A4 = (297.0, 210.0)
MARGIN = 10.0
VIEW_GAP = 12.0  # between the bands of dimensions of neighbouring views
ROW_FIRST = 7.0  # from a view's outline to its first row of dimensions
ROW_STEP = 7.0  # between rows of dimensions
LEVEL_STEP = TEXT + 1.6  # a staggered text further out
LABEL = 3.5  # height of view labels and titles
LABEL_GAP = 4.0  # between a view's outline (or its dimensions below) and its label
SPAN = -1  # the row of a plot spanning all rows of its column, from the top
LEADER_RING = 10.0  # from a view's outline to the balloons around it


@dataclass(frozen=True)
class View:
    """A direction of view: `toward` points from the object to the viewer."""

    name: str
    toward: Vec3
    up: Vec3

    @property
    def right(self) -> Vec3:
        right = bd.Vector(self.up).cross(bd.Vector(self.toward)).normalized()
        return tuple(right)

    @property
    def true_up(self) -> Vec3:
        """`up` made square to the direction of view."""
        return tuple(bd.Vector(self.toward).normalized().cross(bd.Vector(self.right)))

    def project(self, p: Vec3) -> Point2:
        r, u = self.right, self.true_up
        return (
            p[0] * r[0] + p[1] * r[1] + p[2] * r[2],
            p[0] * u[0] + p[1] * u[1] + p[2] * u[2],
        )

    def axis(self, axis: int) -> tuple[int, int] | None:
        """Where a model axis runs in the drawing: (0 across or 1 up, its
        sign), or None when it runs along the direction of view."""
        for i, d in enumerate((self.right, self.true_up)):
            if abs(abs(d[axis]) - 1) < 1e-9:
                return i, int(math.copysign(1, d[axis]))
        return None

    def lines(self, shape: bd.Shape) -> tuple[list[Polyline], list[Polyline]]:
        """The visible and hidden lines of `shape` in this view, in model units."""
        camera = bd.Vector(self.toward).normalized() * 100_000
        visible, hidden = shape.project_to_viewport(camera, viewport_up=self.up, look_at=(0, 0, 0))
        return [_polyline(e) for e in visible], [_polyline(e) for e in hidden]


# Views of a part, by the side of its frame they show, and their cells
# (column, row from the top) in the third-angle layout.
PART_VIEWS = {
    Side.BACK_EDGE: (View("back", (0, 1, 0), (0, 0, -1)), (1, 0)),
    Side.TOP_FACE: (View("top", (0, 0, 1), (0, 1, 0)), (1, 1)),
    Side.LEFT_END: (View("left", (-1, 0, 0), (0, 0, 1)), (0, 2)),
    Side.FRONT_EDGE: (View("front", (0, -1, 0), (0, 0, 1)), (1, 2)),
    Side.RIGHT_END: (View("right", (1, 0, 0), (0, 0, 1)), (2, 2)),
    Side.BOTTOM_FACE: (View("bottom", (0, 0, -1), (0, -1, 0)), (1, 3)),
}
ISO = View("isometric", (1, -1.6, 0.9), (0, 0, 1))  # as the SVG views of export


@dataclass
class Row:
    """A row of dimensions along one drawing axis of a view: a chain through
    `values` (drawing coordinates, model units), or one overall dimension."""

    values: list[float]


@dataclass
class Plot:
    """A view of a shape placed on a sheet, with its rows of dimensions.

    Its cell is the column and row of the layout grid it goes in, or the
    column and `SPAN` to sit at the top of a column of its own beside the
    rows."""

    view: View
    cell: tuple[int, int]
    label: str
    visible: list[Polyline]
    hidden: list[Polyline]
    bounds: tuple[Point2, Point2]  # of the outline in drawing coordinates, model units
    # rows of dimensions by side of the view: "above", "below", "left", "right",
    # innermost first
    rows: dict[str, list[Row]] = field(default_factory=dict)
    balloons: list[tuple[Point2, str]] = field(default_factory=list)  # drawing coordinates
    centres: list[tuple[Point2, float]] = field(default_factory=list)  # of holes, with radii
    # dimensions along model directions (an isometric view): from, to, outwards, text
    dims3d: list[tuple[Vec3, Vec3, Vec3, str]] = field(default_factory=list)
    max_width: float | None = None  # on paper; drawn at a smaller scale if wider
    leaders: bool = False  # balloons around the view, on leaders, rather than on it
    origin: Point2 = (0.0, 0.0)  # on the sheet, of the drawing coordinates (0, 0)
    scale: float = 1.0

    def at(self, p: Point2) -> Point2:
        """A point in drawing coordinates on the sheet."""
        return self.origin[0] + p[0] * self.scale, self.origin[1] + p[1] * self.scale

    @property
    def size(self) -> Point2:
        (u0, v0), (u1, v1) = self.bounds
        return (u1 - u0) * self.scale, (v1 - v0) * self.scale

    def band(self, side: str) -> float:
        """The depth on paper of the dimensions on one side, from the outline."""
        rows = self.rows.get(side, [])
        depth = 0.0
        for i, row in enumerate(rows):
            depth += (ROW_FIRST if i == 0 else ROW_STEP) + _levels(row, self.scale) * LEVEL_STEP
        extra = 12.0 if self.dims3d else 0.0
        if self.leaders:
            extra = LEADER_RING + 3.0
        return depth + (2.0 if rows else 0.0) + extra

    def add_row(self, side: str, values: list[float]) -> None:
        """Add a row of dimensions on a side, outside the ones there, unless
        the same row is already on the opposite side."""
        values = _unique(values)
        opposite = {"above": "below", "below": "above", "left": "right", "right": "left"}[side]
        if len(values) >= 2 and Row(values) not in self.rows.get(opposite, []):
            self.rows.setdefault(side, []).append(Row(values))

    def draw(self, sheet: Sheet) -> None:
        for line in self.hidden:
            sheet.line([self.at(p) for p in line], "hidden")
        for line in self.visible:
            sheet.line([self.at(p) for p in line], "visible")
        for (u, v), radius in self.centres:
            arm = radius + 2 / self.scale
            sheet.line([self.at((u - arm, v)), self.at((u + arm, v))], "center")
            sheet.line([self.at((u, v - arm)), self.at((u, v + arm))], "center")
        if self.leaders:
            self._draw_leaders(sheet)
        placed: list[Point2] = []
        for centre, label in [] if self.leaders else self.balloons:
            x, y = self.at(centre)
            while any(math.hypot(x - a, y - b) < 5.6 for a, b in placed):
                x += 5.8
            placed.append((x, y))
            sheet.balloon((x, y), label)
        (x0, y0), (x1, y1) = self.at(self.bounds[0]), self.at(self.bounds[1])
        for a, b, out, text in self.dims3d:
            pa, pb = self.at(self.view.project(a)), self.at(self.view.project(b))
            o = self.view.project(out)
            k = ROW_FIRST / math.hypot(*o)
            o = (o[0] * k, o[1] * k)
            line_a, line_b = (pa[0] + o[0], pa[1] + o[1]), (pb[0] + o[0], pb[1] + o[1])
            sheet.dimension(pa, pb, line_a, line_b, text)
        for side, rows in self.rows.items():
            offset = 0.0
            for i, row in enumerate(rows):
                offset += ROW_FIRST if i == 0 else ROW_STEP
                self._draw_row(sheet, side, row, offset, (x0, y0, x1, y1))
                offset += _levels(row, self.scale) * LEVEL_STEP
        below = y0 - self.band("below") - LABEL_GAP - LABEL
        sheet.text(((x0 + x1) / 2, below), self.label.upper(), size=LABEL)

    def _draw_leaders(self, sheet: Sheet) -> None:
        """Balloons in a ring around the view, each on a leader to its point,
        in the direction of that point from the view's centre, spread apart."""
        (x0, y0), (x1, y1) = self.at(self.bounds[0]), self.at(self.bounds[1])
        x0, y0, x1, y1 = x0 - LEADER_RING, y0 - LEADER_RING, x1 + LEADER_RING, y1 + LEADER_RING
        w, h = x1 - x0, y1 - y0
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        perimeter = 2 * (w + h)

        def where(t: float) -> Point2:  # along the ring, from its bottom left, anticlockwise
            t %= perimeter
            for length, start, step in (
                (w, (x0, y0), (1, 0)),
                (h, (x1, y0), (0, 1)),
                (w, (x1, y1), (-1, 0)),
                (h, (x0, y1), (0, -1)),
            ):
                if t <= length:
                    return start[0] + step[0] * t, start[1] + step[1] * t
                t -= length
            return x0, y0

        def param(p: Point2) -> float:
            x, y = p
            if abs(y - y0) < 1e-6:
                return x - x0
            if abs(x - x1) < 1e-6:
                return w + y - y0
            if abs(y - y1) < 1e-6:
                return w + h + x1 - x
            return 2 * w + h + y1 - y

        marks = []
        for centre, label in self.balloons:
            ax, ay = self.at(centre)
            dx, dy = ax - cx, ay - cy
            if abs(dx) < 1e-9 and abs(dy) < 1e-9:
                dy = 1.0
            k = min(
                (w / 2) / abs(dx) if abs(dx) > 1e-9 else math.inf,
                (h / 2) / abs(dy) if abs(dy) > 1e-9 else math.inf,
            )
            marks.append([param((cx + dx * k, cy + dy * k)), (ax, ay), label])
        marks.sort(key=lambda m: m[0])
        gap = 6.0
        for prev, mark in pairwise(marks):
            mark[0] = max(mark[0], prev[0] + gap)
        for t, anchor, label in marks:
            at = where(t)
            sheet.line([anchor, at])
            sheet.circle(anchor, 0.5, fill="black")
            sheet.balloon(at, label)

    def _draw_row(
        self, sheet: Sheet, side: str, row: Row, offset: float, box: tuple[float, ...]
    ) -> None:
        x0, y0, x1, y1 = box
        horizontal = side in ("above", "below")
        # the outline's edge facing the row, and the outward direction
        edge, out = {"above": (y1, 1), "below": (y0, -1), "left": (x0, -1), "right": (x1, 1)}[side]
        line = edge + out * offset
        values = [self.at((v, v))[0 if horizontal else 1] for v in row.values]
        texts = _stagger(row, self.scale)
        for (a, b), (text, level, centre) in zip(pairwise(values), texts, strict=True):
            # text above the line, i.e. away from the part when the row is
            # above or on the right
            shift = out * level * LEVEL_STEP
            if horizontal:
                text_line = line + shift + 0.8
                points = (a, edge), (b, edge), (a, line), (b, line)
                text_at = (self.at((centre, centre))[0], text_line)
            else:
                text_line = line + shift - 0.8
                points = (edge, a), (edge, b), (line, a), (line, b)
                text_at = (text_line, self.at((centre, centre))[1])
            sheet.dimension(*points, text, text_at=text_at)


def _levels(row: Row, scale: float) -> int:
    """How many levels of staggered text the row needs beyond the first."""
    return max(level for _, level, _ in _stagger(row, scale))


def _stagger(row: Row, scale: float) -> list[tuple[str, int, float]]:
    """(text, level, centre in drawing coordinates) for each dimension of a
    row. Text goes between the ticks where it fits; at the ends of the row
    beside them; otherwise a level further out, clear of its neighbours."""
    result = []
    ends: dict[int, float] = {}  # where the last text on each level ends, on paper
    pairs = list(pairwise(row.values))
    for i, (a, b) in enumerate(pairs):
        text = _format(b - a)
        half = text_width(text) / 2
        centre = (a + b) / 2 * scale
        fits = (b - a) * scale >= 2 * half + 2 * TICK + 0.6
        if not fits and i == len(pairs) - 1 and ends.get(0, -math.inf) < b * scale:
            centre, level = b * scale + TICK + 0.8 + half, 0
        elif not fits and i == 0:
            centre, level = a * scale - TICK - 0.8 - half, 0
        else:
            for level in range(int(not fits), 4):
                if centre - half >= ends.get(level, -math.inf) + 0.8:
                    break
            else:
                centre = ends[level] + 0.8 + half
        ends[level] = centre + half
        result.append((text, level, centre / scale))
    return result


def _format(value: float) -> str:
    return f"{round(abs(value), 1):g}"


def _unique(values: list[float], eps: float = 0.05) -> list[float]:
    result: list[float] = []
    for v in sorted(values):
        if not result or v - result[-1] > eps:
            result.append(v)
    return result


def _polyline(edge: bd.Edge) -> Polyline:
    if edge.geom_type == bd.GeomType.LINE:
        points = [edge.position_at(0), edge.position_at(1)]
    else:
        n = int(min(128, max(16, edge.length)))
        points = [edge.position_at(i / n) for i in range(n + 1)]
    return [(p.X, p.Y) for p in points]


def _bounds(view: View, lo: Vec3, hi: Vec3) -> tuple[Point2, Point2]:
    corners = [
        view.project((x, y, z))
        for x in (lo[0], hi[0])
        for y in (lo[1], hi[1])
        for z in (lo[2], hi[2])
    ]
    us, vs = [c[0] for c in corners], [c[1] for c in corners]
    return (min(us), min(vs)), (max(us), max(vs))


# --- Layout -------------------------------------------------------------------


@dataclass
class Layout:
    """Plots arranged in a grid of cells on a sheet, above a strip for notes
    and the title block."""

    plots: list[Plot]
    strip: Point2  # width and height of the strip at the bottom, on paper

    def fit(self, page: Point2 = A4) -> Point2:
        """Choose the largest standard scale at which the plots fit the page;
        place them. Returns the size of the sheet (the page, or larger when
        even the smallest scale doesn't fit)."""
        # a long list of notes may make the sheet taller, but not the views smaller
        excess = max(0.0, self.strip[1] - 0.35 * page[1])
        for scale in SCALES:
            size = self._place(scale)
            if size[0] <= page[0] and size[1] - excess <= page[1]:
                break
        return max(size[0], page[0]), max(size[1], page[1])

    def _place(self, scale: float) -> Point2:
        cols: dict[int, list[Plot]] = {}
        rows: dict[int, list[Plot]] = {}
        for plot in self.plots:
            plot.scale = scale
            if plot.max_width and plot.size[0] > plot.max_width:
                plot.scale *= plot.max_width / plot.size[0]
            cols.setdefault(plot.cell[0], []).append(plot)
            if plot.cell[1] != SPAN:
                rows.setdefault(plot.cell[1], []).append(plot)
        # each column: the widest left band, the widest view, the widest right band
        col_x, x = {}, MARGIN
        col_left = {}
        for c in sorted(cols):
            plots = cols[c]
            col_left[c] = max(p.band("left") for p in plots)
            width = max(p.size[0] for p in plots) + max(p.band("right") for p in plots)
            col_x[c] = x
            x += col_left[c] + width + VIEW_GAP
        # rows from the top: the bands above, the views, the bands and labels below
        row_top, y = {}, 0.0
        row_above = {}
        for r in sorted(rows):
            plots = rows[r]
            row_above[r] = max(p.band("above") for p in plots)
            height = max(p.size[1] for p in plots) + max(
                p.band("below") + LABEL_GAP + LABEL for p in plots
            )
            row_top[r] = y
            y += row_above[r] + height + VIEW_GAP
        for plot in [p for p in self.plots if p.cell[1] == SPAN]:
            row_top[SPAN] = 0.0
            tall = plot.band("above") + plot.size[1] + plot.band("below") + LABEL_GAP + LABEL
            y = max(y, tall + VIEW_GAP)
        height = MARGIN + y + self.strip[1] + MARGIN
        width = max(x - VIEW_GAP + MARGIN, self.strip[0] + 2 * MARGIN)
        for plot in self.plots:
            c, r = plot.cell
            (u0, _), (_, v1) = plot.bounds
            left = col_x[c] + col_left[c]
            above = plot.band("above") if r == SPAN else row_above[r]
            top = height - MARGIN - row_top[r] - above
            plot.origin = (left - u0 * plot.scale, top - v1 * plot.scale)
        return width, height


def _scale_text(scale: float) -> str:
    return f"1:{1 / scale:g}" if scale <= 1 else f"{scale:g}:1"


def _title_block(sheet: Sheet, lines: list[tuple[str, str]], scale: float | None) -> None:
    """The title block in the bottom right corner: a title and labelled lines."""
    width, row = 90.0, 6.0
    rows = [*lines, ("scale", f"{_scale_text(scale)}, mm" if scale else "not to scale, mm")]
    x0, y0 = sheet.width - MARGIN - width, MARGIN
    x1, y1 = sheet.width - MARGIN, MARGIN + row * len(rows)
    sheet.rect((x0, y0), (x1, y1))
    for i, (key, value) in enumerate(reversed(rows)):
        y = y0 + i * row
        if i:
            sheet.line([(x0, y), (x1, y)])
        bold = i == len(rows) - 1
        sheet.text((x0 + 2, y + 1.8), key, size=2.0, anchor="start")
        sheet.text(
            (x0 + 22, y + 1.6), value, size=LABEL if bold else 3.0, anchor="start", bold=bold
        )


TITLE_ROWS = 5  # in a title block: name, assembly, size, material, scale


# --- Features -------------------------------------------------------------------


def _side(axis: int, sign: int) -> Side:
    return next(s for s in Side if s.axis == axis and s.sign == sign)


@dataclass
class Feature:
    """What a cut leaves on a part, for dimensioning.

    `coords` are the positions (part frame, by axis) of the surfaces the cut
    leaves inside the blank: the planes of shoulders and cheeks, the corners
    of slanted faces, the axes of holes; for some, the axis of the view that
    shows them best (along a hole, a slanted face edge-on). `opens` are the
    sides of the blank the cut reaches, the side it is cut into first.
    """

    number: int
    text: str
    centre: Vec3
    opens: list[Side]
    coords: list[tuple[int, float, int | None]]  # axis, position, axis of a view to show it in
    holes: list[tuple[int, Vec3, float]]  # axis, a point on it, radius


def features(part: ResolvedPart) -> list[Feature]:
    """The features of a part, one per cut that removes anything, numbered."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.TopAbs import TopAbs_IN

    lo, hi = part.blank
    blank = part.part.blank(lo, hi)
    eps = 1e-3

    def inside(p: bd.Vector) -> bool:
        return BRepClass3d_SolidClassifier(blank.wrapped, p.to_pnt(), 1e-4).State() == TopAbs_IN

    result = []
    for cut in part.cuts:
        removed = cut.removal() & blank
        if removed.volume < eps:
            continue
        box = removed.bounding_box()
        opens = [
            _side(a, sign)
            for a in range(3)
            for sign, reaches in (
                (1, tuple(box.max)[a] >= hi[a] - eps),
                (-1, tuple(box.min)[a] <= lo[a] + eps),
            )
            if reaches
        ]
        own = getattr(cut, "side", None) or getattr(getattr(cut, "arris", None), "a", None)
        if isinstance(own, SideRef) and own.side in opens:
            own_side = own.side
        elif opens:
            # the side it goes into least deep, relative to the part (the end
            # for dovetails, the face for a dado)
            size = [b - a for a, b in zip(lo, hi, strict=True)]
            extent = [b - a for a, b in zip(tuple(box.min), tuple(box.max), strict=True)]
            own_side = min(opens, key=lambda s: extent[s.axis] / size[s.axis])
        else:
            own_side = None
        if own_side is not None:
            opens.remove(own_side)
            opens.insert(0, own_side)

        coords: list[tuple[int, float, int | None]] = []
        holes = []
        for face in removed.faces():
            if not inside(face.position_at(0.5, 0.5)):
                continue  # a face on the outside of the blank, not one the cut leaves
            corners = [tuple(v) for v in face.vertices()]
            if face.geom_type == bd.GeomType.PLANE:
                normal = tuple(face.normal_at())
                axis = next((a for a in range(3) if abs(abs(normal[a]) - 1) < 1e-6), None)
                if axis is not None:
                    coords.append((axis, tuple(face.center())[axis], None))
                else:
                    # seen edge-on (its slope showing) along an axis it doesn't face
                    seen = next((a for a in range(3) if abs(normal[a]) < 1e-6), None)
                    coords += [(a, v, seen) for a, v in _slanted(corners, own_side, lo, hi)]
            elif face.geom_type in (bd.GeomType.CYLINDER, bd.GeomType.CONE):
                surface = BRepAdaptor_Surface(face.wrapped)
                is_cylinder = face.geom_type == bd.GeomType.CYLINDER
                geometry = surface.Cylinder() if is_cylinder else surface.Cone()
                location, direction = geometry.Axis().Location(), geometry.Axis().Direction()
                d = (direction.X(), direction.Y(), direction.Z())
                axis = next((a for a in range(3) if abs(abs(d[a]) - 1) < 1e-6), None)
                if axis is None:
                    continue
                point = (location.X(), location.Y(), location.Z())
                if is_cylinder:
                    holes.append((axis, point, geometry.Radius()))
                if not _on_rod_axis(part, axis, point):
                    coords += [(a, point[a], axis) for a in range(3) if a != axis]
                coords += [(axis, c[axis], None) for c in corners]
            else:
                face_box = face.bounding_box()
                for a in range(3):
                    coords += [(a, tuple(face_box.min)[a], None), (a, tuple(face_box.max)[a], None)]
        coords = [(a, v, seen) for a, v, seen in coords if lo[a] + eps < v < hi[a] - eps]
        centre = tuple(box.center())
        result.append(Feature(len(result) + 1, cut.describe(), centre, opens, coords, holes))
    return result


def _slanted(corners: list[Vec3], own: Side | None, lo: Vec3, hi: Vec3) -> list[tuple[int, float]]:
    """The positions dimensioning a slanted face: where it meets the side the
    cut is made from (nearest the reference face), as a dovetail or a
    chamfer is marked out; and how deep it goes into that side.
    The slope itself is in the cut's description."""
    if own is None:
        return [(a, c[a]) for c in corners for a in range(3)]
    k = own.axis
    plane = hi[k] if own.sign > 0 else lo[k]
    on_side = [c for c in corners if abs(c[k] - plane) < 1e-6] or corners
    # nearest the reference face (for a cut into a face, the reference edge)
    ref, sign = (2, 1) if k != 2 else (1, -1)
    nearest = max(sign * c[ref] for c in on_side)
    marked = [c for c in on_side if abs(sign * c[ref] - nearest) < 1e-6]
    return [(a, c[a]) for c in marked for a in range(3) if a != k] + [(k, c[k]) for c in corners]


def _on_rod_axis(part: ResolvedPart, axis: int, point: Vec3) -> bool:
    """Whether a round feature is centred on a rod's axis (a round tenon)."""
    if not isinstance(part.part, Rod) or axis != 0:
        return False
    y, z = part.part.axis
    return abs(point[1] - y) < 1e-6 and abs(point[2] - z) < 1e-6


def _assign(
    feats: list[Feature], order: list[Side], defaults: list[Side]
) -> dict[tuple[Side, int], list[Feature]]:
    """Choose a view for each coordinate of each feature: the first side the
    feature opens to whose view shows that axis (its own side first, but a
    view showing a coordinate best before), else the first default view
    showing it (dimensioned to hidden lines). Returns the features by view
    and axis, with only the coordinates shown there."""
    chosen: dict[tuple[Side, int], list[Feature]] = {}
    for feat in feats:
        candidates = feat.opens[:1] + [s for s in order if s in feat.opens[1:]]
        shown: dict[tuple[Side, int], list] = {}
        for axis, value, seen in feat.coords:
            preferred = [s for s in candidates if s.axis == seen] + candidates
            side = next((s for s in preferred if s.axis != axis), None)
            side = side or next(s for s in defaults if s.axis != axis)
            shown.setdefault((side, axis), []).append((axis, value, None))
        for key, coords in shown.items():
            chosen.setdefault(key, []).append(replace(feat, coords=coords))
    return chosen


# --- Part sheets ----------------------------------------------------------------

NOTE = 3.0  # height of the text of notes
NOTE_LINE = 4.6


def part_sheet(model: ResolvedModel, part: ResolvedPart) -> Sheet:
    """A shop drawing of one part: its views with overall and feature
    dimensions, the features numbered and described, and a title block."""
    shape = part.shape
    rod = isinstance(part.part, Rod)
    if rod:
        defaults = [Side.FRONT_EDGE, Side.RIGHT_END]
        order = [*defaults, Side.LEFT_END, Side.TOP_FACE, Side.BOTTOM_FACE, Side.BACK_EDGE]
    else:
        defaults = [Side.TOP_FACE, Side.FRONT_EDGE]
        order = [*defaults, Side.RIGHT_END, Side.LEFT_END, Side.BOTTOM_FACE, Side.BACK_EDGE]
    feats = features(part)
    chosen = _assign(feats, order, defaults)
    sides = [s for s in order if s in defaults or any(v == s for v, _ in chosen)]
    plots: dict[Side | None, Plot] = {side: _plot(part, side, shape) for side in sides}

    # chains of feature dimensions, inside the overall ones: on the side of
    # the view nearest each feature, one chain per side
    for (side, axis), shown in chosen.items():
        plot = plots[side]
        i, sign = plot.view.axis(axis)
        bounds = [plot.bounds[0][i], plot.bounds[1][i]]
        chains: dict[str, list[float]] = {}
        for feat in shown:
            near = _near_side(plot, i, plot.view.project(feat.centre))
            chains.setdefault(near, []).extend(sign * v for _, v, _ in feat.coords)
        for near, values in sorted(chains.items(), key=lambda c: c[0] != _row_side(plot, i)):
            plot.add_row(near, bounds + values)
    # overall dimensions, outermost
    if rod:
        front = plots[Side.FRONT_EDGE]
        front.add_row("below", [front.bounds[0][0], front.bounds[1][0]])
        front.add_row("left", [front.bounds[0][1], front.bounds[1][1]])
    else:
        top, front = plots[Side.TOP_FACE], plots[Side.FRONT_EDGE]
        top.add_row("above", [top.bounds[0][0], top.bounds[1][0]])
        top.add_row("left", [top.bounds[0][1], top.bounds[1][1]])
        front.add_row("left", [front.bounds[0][1], front.bounds[1][1]])

    plots[None] = _iso(shape, part.blank, rod)

    # each feature numbered in the first view dimensioning it (else showing
    # it); holes' centre lines
    for feat in feats:
        dimensioned = {s for (s, _), fs in chosen.items() if feat.number in {f.number for f in fs}}
        shown = [s for s in sides if s in dimensioned] or [s for s in feat.opens if s in plots]
        plot = plots[shown[0]] if shown else plots[defaults[0]]
        plot.balloons.append((plot.view.project(feat.centre), str(feat.number)))
        for axis, point, radius in feat.holes:
            for p in plots.values():
                if p.view.axis(axis) is None:
                    p.centres.append((p.view.project(point), radius))

    notes = [f"{f.number}  {f.text}" for f in feats]
    strip = max(TITLE_ROWS * 6.0, len(notes) * NOTE_LINE) + 4
    layout = Layout(list(plots.values()), strip=(0.0, strip))
    sheet = Sheet(*layout.fit())
    for plot in layout.plots:
        plot.draw(sheet)
    _notes(sheet, notes)
    _title_block(sheet, _part_title(model, part), layout.plots[0].scale)
    return sheet


def _iso(
    shape: bd.Shape,
    blank: tuple[Vec3, Vec3],
    rod: bool = False,
    cell: tuple[int, int] = (2, 1),
    label: str = "isometric",
) -> Plot:
    """An isometric view (from the front right, above) with the overall
    dimensions along its edges, by default in the top right corner."""
    visible, _ = ISO.lines(shape)
    lo, hi = blank
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    dims = [((x0, y0, z0), (x1, y0, z0), (0, -1, 0), _format(x1 - x0))]
    if not rod:
        dims.append(((x1, y0, z0), (x1, y1, z0), (1, 0, 0), _format(y1 - y0)))
        dims.append(((x0, y0, z0), (x0, y0, z1), (-1, 0, 0), _format(z1 - z0)))
    plot = Plot(ISO, cell, label, visible, [], _bounds(ISO, lo, hi), dims3d=dims)
    plot.max_width = 80.0
    return plot


def _row_side(plot: Plot, i: int) -> str:
    """Where a view's dimensions along drawing axis `i` go: outside the sheet's
    middle (above the top views, on the right of the right ones)."""
    col, row = plot.cell
    if i == 0:
        return "above" if row < 2 else "below"
    return "right" if col > 1 else "left"


def _near_side(plot: Plot, i: int, p: Point2) -> str:
    """The side of a view across drawing axis `i` nearest to a point; the
    outer side when it lies in the middle third."""
    lo, hi = plot.bounds[0][1 - i], plot.bounds[1][1 - i]
    t = (p[1 - i] - lo) / ((hi - lo) or 1)
    if 1 / 3 <= t <= 2 / 3:
        return _row_side(plot, i)
    if i == 0:
        return "above" if t > 0.5 else "below"
    return "right" if t > 0.5 else "left"


def _notes(sheet: Sheet, notes: list[str]) -> None:
    """Numbered notes in the bottom left corner, from the top of the strip down."""
    width = sheet.width - 2 * MARGIN - 90 - 10
    chars = int(width / text_width("x", NOTE))
    y = MARGIN + len(notes) * NOTE_LINE
    for note in notes:
        sheet.text((MARGIN, y - NOTE_LINE + 1), note[:chars], size=NOTE, anchor="start")
        y -= NOTE_LINE


def _plot(part: ResolvedPart, side: Side, shape: bd.Shape) -> Plot:
    view, cell = PART_VIEWS[side]
    visible, hidden = view.lines(shape)
    label = SideRef(part.part, side).name.replace("_", " ")
    if isinstance(part.part, Rod) and side.axis != 0:
        label = "side"
    return Plot(view, cell, label, visible, hidden, _bounds(view, *part.blank))


def _part_title(model: ResolvedModel, part: ResolvedPart) -> list[tuple[str, str]]:
    p = part.part
    size = _part_title_size(part)
    material = p.stock.species + (", mirror image" if p.mirror else "")
    return [
        ("part", p.name),
        ("of", model.name),
        ("cut size", size),
        ("material", material.strip(", ")),
    ]


# --- Assembly sheets ------------------------------------------------------------

# Views of an assembly, Z up, the front towards -y, and their cells.
ASSEMBLY_VIEWS = {
    "top": (View("top", (0, 0, 1), (0, 1, 0)), (1, 0)),
    "front": (View("front", (0, -1, 0), (0, 0, 1)), (1, 1)),
    "right side": (View("right", (1, 0, 0), (0, 0, 1)), (2, 1)),
}


def assembly_sheet(model: ResolvedModel) -> Sheet:
    """A drawing of the whole assembly: front, top and side views with the
    overall dimensions (no hidden lines), and an isometric view."""
    shape = model.compound()
    box = shape.bounding_box()
    lo, hi = tuple(box.min), tuple(box.max)
    plots = {}
    for label, (view, cell) in ASSEMBLY_VIEWS.items():
        visible, _ = view.lines(shape)
        plots[label] = Plot(view, cell, label, visible, [], _bounds(view, lo, hi))
    front, side = plots["front"], plots["right side"]
    front.add_row("below", [front.bounds[0][0], front.bounds[1][0]])
    front.add_row("left", [front.bounds[0][1], front.bounds[1][1]])
    side.add_row("below", [side.bounds[0][0], side.bounds[1][0]])
    iso = _iso(shape, (lo, hi), cell=(3, SPAN))
    iso.max_width = 110.0

    layout = Layout([*plots.values(), iso], strip=(0.0, TITLE_ROWS * 6.0 + 4))
    sheet = Sheet(*layout.fit())
    for plot in layout.plots:
        plot.draw(sheet)
    _title_block(sheet, _assembly_title(model, lo, hi), front.scale)
    return sheet


def parts_sheet(model: ResolvedModel) -> Sheet:
    """The parts of an assembly: an exploded isometric view with the parts
    numbered, and a list of them with their cut sizes."""
    from woodwright.export import exploded

    apart = exploded(model)
    visible, _ = ISO.lines(apart)
    box = apart.bounding_box()
    blown = Plot(ISO, (0, 0), "exploded", visible, [], _bounds(ISO, tuple(box.min), tuple(box.max)))
    blown.leaders = True
    for number, child in enumerate(apart.children, 1):
        blown.balloons.append((ISO.project(tuple(child.bounding_box().center())), str(number)))

    rows = [_part_row(i, part) for i, part in enumerate(model.parts, 1)]
    widths = _column_widths(rows)
    list_width = sum(widths)
    title = TITLE_ROWS * 6.0
    layout = Layout([blown], strip=(0.0, title + 4))
    width, height = layout.fit(page=(A4[0] - list_width - MARGIN, A4[1]))
    list_height = (len(rows) + 1) * NOTE_LINE
    sheet = Sheet(
        max(A4[0], width + list_width + MARGIN),
        max(height, 3 * MARGIN + list_height + title),
    )
    for plot in layout.plots:  # to the top of a taller sheet
        plot.origin = (plot.origin[0], plot.origin[1] + sheet.height - height)
        plot.draw(sheet)
    _parts_list(sheet, rows, widths, (sheet.width - MARGIN - list_width, sheet.height - MARGIN))
    shape_box = model.compound().bounding_box()
    _title_block(sheet, _assembly_title(model, tuple(shape_box.min), tuple(shape_box.max)), None)
    return sheet


def _assembly_title(model: ResolvedModel, lo: Vec3, hi: Vec3) -> list[tuple[str, str]]:
    width, depth, height = (b - a for a, b in zip(lo, hi, strict=True))
    return [
        ("assembly", model.name),
        ("parts", str(len(model.parts))),
        ("overall", f"{_format(width)} x {_format(depth)} x {_format(height)} (W x D x H)"),
        ("material", ", ".join(sorted({p.part.stock.species for p in model.parts}))),
    ]


def _part_row(number: int, part: ResolvedPart) -> list[str]:
    size = _part_title_size(part)
    note = "mirror image" if part.part.mirror else ""
    return [str(number), part.part.name, size, part.part.stock.species, note]


def _part_title_size(part: ResolvedPart) -> str:
    if isinstance(part.part, Rod):
        return f"ø{part.part.diameter:g} x {part.size[0]:g}"
    return " x ".join(f"{x:g}" for x in part.size)


PARTS_HEADER = ["no.", "part", "cut size (L x W x T)", "material", ""]


def _column_widths(rows: list[list[str]]) -> list[float]:
    columns = [PARTS_HEADER, *rows]
    return [max(text_width(r[i], NOTE) for r in columns) + 4 for i in range(len(PARTS_HEADER))]


def _parts_list(sheet: Sheet, rows: list[list[str]], widths: list[float], top_left: Point2) -> None:
    """The parts list: a header and a line per part, down from `top_left`."""
    x0, y = top_left
    for i, row in enumerate([PARTS_HEADER, *rows]):
        x = x0
        for text, width in zip(row, widths, strict=True):
            sheet.text((x, y - NOTE_LINE + 1), text, size=NOTE, anchor="start", bold=i == 0)
            x += width
        if i == 0:
            sheet.line([(x0, y - NOTE_LINE), (x, y - NOTE_LINE)])
        y -= NOTE_LINE
