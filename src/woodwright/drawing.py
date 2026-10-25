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
import textwrap
from collections import Counter
from dataclasses import dataclass, field, replace
from itertools import pairwise

import build123d as bd
from OCP.Standard import Standard_ConstructionError, Standard_Failure

from woodwright.assembly import ResolvedModel, ResolvedPart
from woodwright.grouping import PartGroup, cut_shape, local
from woodwright.part import Rod, Side, SideRef
from woodwright.sheet import TEXT, TICK, Point2, Sheet, text_width

Vec3 = tuple[float, float, float]
Polyline = list[Point2]

# the ISO 5455 scales and the in-between ones common in woodworking plans
SCALES = [2, 1, 1 / 2, 1 / 2.5, 1 / 4, 1 / 5, 1 / 8, 1 / 10, 1 / 15, 1 / 20, 1 / 25, 1 / 50]
A4 = (297.0, 210.0)
MARGIN = 10.0
VIEW_GAP = 10.0  # between the bands of dimensions of neighbouring views
ROW_FIRST = 7.0  # from a view's outline to its first row of dimensions
ROW_STEP = 7.0  # between rows of dimensions
LEVEL_STEP = TEXT + 1.6  # a staggered text further out
LABEL = 3.5  # height of view labels and titles
LABEL_GAP = 4.0  # between a view's outline (or its dimensions below) and its label
ISO_SIZES = [110.0, 90.0, 70.0, 55.0, 40.0]  # the largest an isometric view is drawn, on paper
END_ZOOM = (70.0, 50.0)  # the largest an end view is enlarged to, on paper
DETAIL_ZOOM = (70.0, 45.0)  # the largest a detail is enlarged to, on paper
MIN_SEGMENT = 2.5  # the shortest dimension on paper that reads well, else a detail
DETAIL_MARGIN = 8.0  # around a feature in a detail, model units
DETAIL_ENLARGES = 1.5  # at least, else the feature stays in its view
DETAIL_ROUNDS = 4  # of choosing details and fitting the sheet, at most
BALLOON = 2.6  # radius of a balloon
BALLOON_GAP = 3.0  # between the dimensions on a side and the balloons past them
BALLOON_SPACING = 6.0  # between the centres of balloons in a line
MAX_LEADERS = 4  # from a balloon to identical features, else to one of them
ROW_COST = 25.0  # of crossing a row of dimensions with a leader, as mm of leader across a view
PACK_GAP = 8.0  # between the views placed in the space the grid leaves
LEADER_RING = 10.0  # from a view's outline to the balloons around it
THIN_EDGES = 3.0  # the median length of edges on paper for thin lines, below it
MEDIUM_EDGES = 8.0  # for medium lines


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

    Its cell is the column and row of the layout grid it goes in, or None
    for a view placed in the space the grid leaves (see `Layout`)."""

    view: View
    cell: tuple[int, int] | None
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
    leaders: bool = False  # balloons around the view, on leaders, rather than on it
    flexible: bool = False  # not to scale, as large as there is room for (an isometric view)
    # the largest size on paper the view may be enlarged to, beyond the sheet's scale
    zoom: Point2 | None = None
    zoomed: bool = False  # drawn at a larger scale than the sheet's
    crop: bool = False  # a detail: a part of a view, with break lines where it cuts the part
    side: Side | None = None  # of a part shown in the view (or detailed)
    numbers: list[int] = field(default_factory=list)  # of the features a detail shows
    # for a detail, the plot it enlarges and the point it shows (drawing coordinates)
    parent: tuple[Plot, Point2] | None = None
    origin: Point2 = (0.0, 0.0)  # on the sheet, of the drawing coordinates (0, 0)
    scale: float = 1.0
    lines: str | None = None  # the line weight, if not the view's own (see `weight`)

    def at(self, p: Point2) -> Point2:
        """A point in drawing coordinates on the sheet."""
        return self.origin[0] + p[0] * self.scale, self.origin[1] + p[1] * self.scale

    @property
    def size(self) -> Point2:
        (u0, v0), (u1, v1) = self.bounds
        return (u1 - u0) * self.scale, (v1 - v0) * self.scale

    def extent(self) -> tuple[float, float, float, float]:
        """How far the plot reaches beyond its outline on paper, with its
        dimensions and label: left, right, above, below."""
        left, right = self.band("left"), self.band("right")
        overhang = (text_width(self.title(), LABEL) - self.size[0] - left - right) / 2
        if overhang > 0:
            left, right = left + overhang, right + overhang
        return left, right, self.band("above"), self.band("below") + LABEL_GAP + LABEL

    def footprint(self) -> Point2:
        left, right, above, below = self.extent()
        return left + self.size[0] + right, above + self.size[1] + below

    def title(self) -> str:
        """The label, with the scale when it isn't the sheet's."""
        label = self.label.upper()
        return f"{label}  {_scale_text(self.scale)}" if self.zoom and self.zoomed else label

    def band(self, side: str) -> float:
        """The depth on paper of the dimensions (and balloons) on one side,
        from the outline."""
        extra = 12.0 if self.dims3d else 0.0
        if self.leaders:
            extra = LEADER_RING + 3.0
        if side in self.callouts():
            extra += BALLOON_GAP + 2 * BALLOON
        return self._rows_depth(side) + extra

    def _rows_depth(self, side: str) -> float:
        rows = self.rows.get(side, [])
        depth = 0.0
        for i, row in enumerate(rows):
            depth += (ROW_FIRST if i == 0 else ROW_STEP) + _levels(row, self.scale) * LEVEL_STEP
        return depth + (2.0 if rows else 0.0)

    def callouts(self) -> dict[str, list[tuple[list[Point2], str]]]:
        """The balloons by the side of the view they go on, outside its
        dimensions: the side cheapest to reach, crossing few rows of
        dimensions and little of the view. Balloons with the same label
        (identical features) are one, on leaders to each of them, or for
        more than `MAX_LEADERS`, to the one nearest its side."""
        if self.leaders:
            return {}
        (u0, v0), (u1, v1) = self.bounds
        anchors: dict[str, list[Point2]] = {}
        for point, label in self.balloons:
            anchors.setdefault(label, []).append(point)

        def inside(p: Point2) -> dict[str, float]:
            u, v = p
            return {"above": v1 - v, "below": v - v0, "left": u - u0, "right": u1 - u}

        def cost(side: str, points: list[Point2]) -> float:
            depth = sum(inside(p)[side] for p in points) / len(points)
            return len(self.rows.get(side, [])) * ROW_COST + 2 * depth * self.scale

        sides: dict[str, list[tuple[list[Point2], str]]] = {}
        for label, points in anchors.items():
            side = min(("above", "below", "left", "right"), key=lambda s: cost(s, points))
            if len(points) > MAX_LEADERS:
                points = [min(points, key=lambda p: inside(p)[side])]
            sides.setdefault(side, []).append((points, label))
        return sides

    def add_row(self, side: str, values: list[float]) -> None:
        """Add a row of dimensions on a side, outside the ones there, unless
        the same row is already on the opposite side."""
        values = _unique(values)
        opposite = {"above": "below", "below": "above", "left": "right", "right": "left"}[side]
        if len(values) >= 2 and Row(values) not in self.rows.get(opposite, []):
            self.rows.setdefault(side, []).append(Row(values))

    def weight(self) -> str:
        """The line weight of the view (a suffix of the style): thinner where
        its edges are short on paper, so that small details don't fill in."""
        if self.lines is not None:
            return self.lines
        lengths = sorted(
            sum(math.dist(a, b) for a, b in pairwise(line)) * self.scale for line in self.visible
        )
        median = lengths[len(lengths) // 2] if lengths else math.inf
        return "-s" if median < THIN_EDGES else "-m" if median < MEDIUM_EDGES else ""

    def draw(self, sheet: Sheet) -> None:
        weight = self.weight()
        for line in self.hidden:
            sheet.line([self.at(p) for p in line], "hidden-s" if weight == "-s" else "hidden")
        for line in self.visible:
            sheet.line([self.at(p) for p in line], "visible" + weight)
        if self.crop and self.parent:
            self._draw_breaks(sheet)
        for (u, v), radius in self.centres:
            arm = radius + 2 / self.scale
            sheet.line([self.at((u - arm, v)), self.at((u + arm, v))], "center")
            sheet.line([self.at((u, v - arm)), self.at((u, v + arm))], "center")
        if self.leaders:
            self._draw_leaders(sheet)
        (x0, y0), (x1, y1) = self.at(self.bounds[0]), self.at(self.bounds[1])
        for side, callouts in self.callouts().items():
            self._draw_callouts(sheet, side, callouts, (x0, y0, x1, y1))
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
        sheet.text(((x0 + x1) / 2, below), self.title(), size=LABEL)

    def _draw_breaks(self, sheet: Sheet) -> None:
        """Break lines where a detail cuts the part: thin, with a zigzag."""
        (u0, v0), (u1, v1) = self.bounds
        (pu0, pv0), (pu1, pv1) = self.parent[0].bounds
        eps = 1e-6
        sides = [
            (u0 > pu0 + eps, (u0, v0), (u0, v1)),
            (u1 < pu1 - eps, (u1, v0), (u1, v1)),
            (v0 > pv0 + eps, (u0, v0), (u1, v0)),
            (v1 < pv1 - eps, (u0, v1), (u1, v1)),
        ]
        for cuts, a, b in sides:
            if not cuts:
                continue
            sheet.line(_break_line(self.at(a), self.at(b)))

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

    def _draw_callouts(
        self,
        sheet: Sheet,
        side: str,
        callouts: list[tuple[list[Point2], str]],
        box: tuple[float, ...],
    ) -> None:
        """Balloons in a line beside one side of the view, past its
        dimensions, each on leaders to dots on its features, spread apart."""
        x0, y0, x1, y1 = box
        horizontal = side in ("above", "below")
        edge, out = {"above": (y1, 1), "below": (y0, -1), "left": (x0, -1), "right": (x1, 1)}[side]
        line = edge + out * (self._rows_depth(side) + BALLOON_GAP + BALLOON)
        k = 0 if horizontal else 1
        marks = sorted(
            (
                [
                    sum(self.at(c)[k] for c in points) / len(points),
                    [self.at(c) for c in points],
                    label,
                ]
                for points, label in callouts
            ),
            key=lambda m: m[0],
        )
        # spread apart, then centred again on where they belong
        spread = [m[0] for m in marks]
        for i in range(1, len(spread)):
            spread[i] = max(spread[i], spread[i - 1] + BALLOON_SPACING)
        shift = sum(m[0] for m in marks) / len(marks) - sum(spread) / len(spread)
        for along, (_, anchors, label) in zip(spread, marks, strict=True):
            at = (along + shift, line) if horizontal else (line, along + shift)
            for anchor in anchors:
                d = math.dist(anchor, at)
                if d > BALLOON:
                    t = (d - BALLOON) / d
                    end = anchor[0] + (at[0] - anchor[0]) * t, anchor[1] + (at[1] - anchor[1]) * t
                    sheet.line([anchor, end])
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


WEIGHTS = ["-s", "-m", ""]  # thin to thick


def _same_weight(plots: list[Plot]) -> None:
    """Draw the orthographic views of a sheet with the same lines: the
    thinnest any of them needs."""
    weight = min((p.weight() for p in plots), key=WEIGHTS.index)
    for plot in plots:
        plot.lines = weight


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
    try:
        if edge.geom_type == bd.GeomType.LINE:
            points = [edge.position_at(0), edge.position_at(1)]
        else:
            n = int(min(128, max(16, edge.length)))
            points = [edge.position_at(i / n) for i in range(n + 1)]
    # A degenerate edge from the projection. (The bindings don't keep OCCT's
    # hierarchy: a construction error isn't a Standard_Failure in Python.)
    except Standard_Failure, Standard_ConstructionError:
        points = [bd.Vector(*v) for v in edge.vertices()]
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


Rect = tuple[float, float, float, float]  # left, top, right, bottom; y down from the top


@dataclass
class Layout:
    """Plots on a sheet: the orthographic views in a grid of cells (column,
    row from the top) from the top left, above a strip for notes and the
    title block; the others (`cell` None: an isometric view, details) in the
    space left, each as near as can be to where it belongs."""

    plots: list[Plot]
    notes: Point2 = (0.0, 0.0)  # size on paper of the notes in the bottom left corner
    scale: float = 1.0  # the scale chosen by `fit`

    def fit(self, page: Point2 = A4) -> Point2:
        """Choose the largest standard scale at which the plots fit the page,
        then the largest enlarged views and isometric views; place them.
        Returns the size of the sheet: the page, or taller when even the
        smallest scale doesn't fit."""
        # a long list of notes may make the sheet taller, but not the views smaller
        height = page[1] + max(0.0, self._strip() - 0.35 * page[1])
        for scale in SCALES:
            for option in self._options(scale):
                if self._place(scale, *option, (page[0], height)):
                    return page[0], height
        # too tall at any scale (many views of a long thin part, many notes):
        # the sheet grows taller, as little as it can
        wide = [s for s in SCALES if self._grid(s, 0, (0, 0))[0] + 2 * MARGIN <= page[0]]
        width = page[0] if wide else self._grid(SCALES[-1], 0, (0, 0))[0] + 2 * MARGIN
        while True:
            height += 10.0
            for scale in wide or SCALES[-1:]:
                for option in self._options(scale):
                    if self._place(scale, *option, (width, height)):
                        return width, height

    def _strip(self) -> float:
        return max(TITLE_ROWS * 6.0, self.notes[1]) + 4

    def _options(self, scale: float) -> list[tuple[int, float]]:
        """Ways to draw the enlarged and isometric views, the largest first:
        how many scales down from its largest each enlarged view is, the
        size of the isometric views."""
        steps = max((_zoom_steps(p, scale) for p in self.plots if p.zoom), default=0)
        sizes = ISO_SIZES if any(p.flexible for p in self.plots) else ISO_SIZES[:1]
        return [(step, size) for step in range(steps + 1) for size in sizes]

    def _scales(self, scale: float, step: int, iso: float) -> None:
        for plot in self.plots:
            plot.scale = scale
            if plot.zoom:
                # a detail at least somewhat larger than its view (if there's
                # no room for it, the sheet's scale gives way)
                least = scale * (DETAIL_ENLARGES if plot.crop else 1)
                smallest = max((i for i, s in enumerate(SCALES) if s >= least - 1e-9), default=0)
                largest = min(SCALES.index(scale) - _zoom_steps(plot, scale), smallest)
                plot.scale = SCALES[min(largest + step, smallest)]
                plot.zoomed = plot.scale > scale
            if plot.flexible:
                plot.scale = 1.0
                plot.scale = iso / max(plot.size)

    def _grid(self, scale: float, step: int, at: Point2) -> tuple[float, float]:
        """Place the grid's plots from `at`, top left (y down); returns the
        width and height of the grid on paper."""
        self._scales(scale, step, ISO_SIZES[0])
        grid = [p for p in self.plots if p.cell is not None]
        cols: dict[int, list[Plot]] = {}
        rows: dict[int, list[Plot]] = {}
        for plot in grid:
            cols.setdefault(plot.cell[0], []).append(plot)
            rows.setdefault(plot.cell[1], []).append(plot)
        # each column: the widest left reach, the widest view, the widest right reach
        col_x, col_left, col_width, x = {}, {}, {}, at[0]
        for c in sorted(cols):
            col_left[c] = max(p.extent()[0] for p in cols[c])
            col_width[c] = max(p.size[0] for p in cols[c])
            col_x[c] = x
            x += col_left[c] + col_width[c] + max(p.extent()[1] for p in cols[c]) + VIEW_GAP
        # each row from the top: above, the views, below with the labels
        row_y, row_above, row_height, y = {}, {}, {}, at[1]
        for r in sorted(rows):
            row_above[r] = max(p.extent()[2] for p in rows[r])
            row_height[r] = max(p.size[1] for p in rows[r])
            row_y[r] = y
            y += row_above[r] + row_height[r] + max(p.extent()[3] for p in rows[r]) + VIEW_GAP
        for plot in grid:  # centred in its cell (views at another scale)
            c, r = plot.cell
            w, h = plot.size
            left = col_x[c] + col_left[c] + (col_width[c] - w) / 2
            top = row_y[r] + row_above[r] + (row_height[r] - h) / 2
            plot.origin = (left, top)  # for now, top left of the outline, y down
        return (x - VIEW_GAP - at[0] if grid else 0.0), (y - VIEW_GAP - at[1] if grid else 0.0)

    def _place(self, scale: float, step: int, iso: float, size: Point2) -> bool:
        """Place the plots on a sheet of `size`, if they fit."""
        width, height = self._grid(scale, step, (MARGIN, MARGIN))
        if MARGIN + width > size[0] - MARGIN or MARGIN + height > size[1] - MARGIN - self._strip():
            return False
        self._scales(scale, step, iso)
        grid = [p for p in self.plots if p.cell is not None]
        taken = [_rect(p, p.origin) for p in grid]
        bottom = size[1] - MARGIN
        taken.append((MARGIN, bottom - self.notes[1], MARGIN + self.notes[0], bottom))
        right = size[0] - MARGIN
        taken.append((right - TITLE_WIDTH, bottom - TITLE_ROWS * 6.0, right, bottom))
        area = (MARGIN, MARGIN, right, bottom)
        loose = {}
        for plot in sorted(self.plots, key=lambda p: -p.size[0] * p.size[1]):
            if plot.cell is None:
                if plot.parent:
                    parent, point = plot.parent
                    near = _paper(parent, point)
                else:
                    near = (area[2], area[1])  # the top right corner
                at = _pack(plot, taken, area, near)
                if at is None:
                    return False
                loose[id(plot)] = at
                taken.append(_rect(plot, at))
        for plot in self.plots:  # origins of the drawing coordinates, y up
            left, top = loose.get(id(plot), plot.origin)
            (u0, _), (_, v1) = plot.bounds
            plot.origin = (left - u0 * plot.scale, size[1] - top - v1 * plot.scale)
        self.scale = scale
        return True


def _break_line(a: Point2, b: Point2) -> Polyline:
    """A thin break line from `a` to `b`, a little beyond, with a zigzag in the middle."""
    length = math.dist(a, b)
    t = ((b[0] - a[0]) / length, (b[1] - a[1]) / length)
    n = (-t[1], t[0])
    m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)

    def at(base: Point2, along: float, across: float = 0.0) -> Point2:
        return base[0] + t[0] * along + n[0] * across, base[1] + t[1] * along + n[1] * across

    zigzag = [at(m, -1.2), at(m, -0.4, 1.5), at(m, 0.4, -1.5), at(m, 1.2)]
    return [at(a, -2.0), *zigzag, at(b, 2.0)]


def _zoom_steps(plot: Plot, scale: float) -> int:
    """How many standard scales above the sheet's an enlarged view can be."""
    (u0, v0), (u1, v1) = plot.bounds
    w, h = plot.zoom
    fits = [s for s in SCALES if (u1 - u0) * s <= w and (v1 - v0) * s <= h]
    return max(0, SCALES.index(scale) - SCALES.index(fits[0])) if fits else 0


def _paper(plot: Plot, p: Point2) -> Point2:
    """Where a point in drawing coordinates of a grid plot is (placed, not yet
    with its origin: top left of the outline, y down)."""
    (u0, _), (_, v1) = plot.bounds
    return plot.origin[0] + (p[0] - u0) * plot.scale, plot.origin[1] + (v1 - p[1]) * plot.scale


def _rect(plot: Plot, at: Point2) -> Rect:
    """The space a plot takes with its outline's top left corner at `at` (y down)."""
    left, right, above, below = plot.extent()
    w, h = plot.size
    return at[0] - left, at[1] - above, at[0] + w + right, at[1] + h + below


def _pack(plot: Plot, taken: list[Rect], area: Rect, near: Point2) -> Point2 | None:
    """Where to put a plot clear of the `taken` space in `area`, as near to
    `near` as can be: the top left corner of its outline (y down), or None."""
    left, _, above, _ = plot.extent()
    w, h = plot.footprint()
    xs = {area[0], area[2] - w}
    ys = {area[1], area[3] - h}
    for r in taken:
        xs |= {r[2] + PACK_GAP, r[0] - PACK_GAP - w}
        ys |= {r[3] + PACK_GAP, r[1] - PACK_GAP - h}
    best, best_distance = None, math.inf
    for x in xs:
        for y in ys:
            rect = (x, y, x + w, y + h)
            inside = area[0] <= x and x + w <= area[2] and area[1] <= y and y + h <= area[3]
            if not inside or any(_overlap(rect, r, PACK_GAP - 1e-6) for r in taken):
                continue
            distance = math.dist(((x + x + w) / 2, (y + y + h) / 2), near)
            if distance < best_distance:
                best, best_distance = (x + left, y + above), distance
    return best


def _overlap(a: Rect, b: Rect, gap: float = 0.0) -> bool:
    """Whether two rectangles are nearer than `gap`."""
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


def _scale_text(scale: float) -> str:
    return f"1:{1 / scale:g}" if scale <= 1 else f"{scale:g}:1"


def _title_block(sheet: Sheet, lines: list[tuple[str, str]], scale: float | None) -> None:
    """The title block in the bottom right corner: a title and labelled lines."""
    width, row = TITLE_WIDTH, 6.0
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


TITLE_WIDTH = 90.0
TITLE_ROWS = 6  # in a title block, at most: name, assembly, quantity, size, material, scale


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
    Identical features (cuts differing only in where they are) share their
    `label`, the number they are called out by.
    """

    number: int
    text: str
    centre: Vec3
    opens: list[Side]
    coords: list[tuple[int, float, int | None]]  # axis, position, axis of a view to show it in
    holes: list[tuple[int, Vec3, float]]  # axis, a point on it, radius
    label: int = 0


def features(part: ResolvedPart) -> list[Feature]:
    """The features of a part, one per cut that removes anything, numbered,
    and labelled by their descriptions without positions (identical ones
    alike)."""
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
                elif _at_45(normal):
                    pass  # a chamfer or a mitre: its size is in the note
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
        text = local(cut_shape(cut), part.part)
        result.append(Feature(len(result) + 1, text, centre, opens, coords, holes))
    labels: dict[str, int] = {}
    for feat in result:
        feat.label = labels.setdefault(feat.text, len(labels) + 1)
    return result


def _at_45(normal: Vec3) -> bool:
    """Whether a plane is at 45 degrees to two axes of the part, along the third."""
    small, a, b = sorted(abs(n) for n in normal)
    return small < 1e-6 and abs(a - math.sqrt(0.5)) < 1e-6 and abs(b - math.sqrt(0.5)) < 1e-6


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
    dimensions, the features numbered and described, and a title block;
    for a group of identical parts, with their number and names."""
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
    _dimension(plots, chosen, rod)
    plots[None] = _iso(shape, part.blank, rod)

    # each feature numbered in the first view dimensioning it (else showing
    # it); holes' centre lines
    for feat in feats:
        dimensioned = {s for (s, _), fs in chosen.items() if feat.number in {f.number for f in fs}}
        shown = [s for s in sides if s in dimensioned] or [s for s in feat.opens if s in plots]
        plot = plots[shown[0]] if shown else plots[defaults[0]]
        plot.balloons.append((plot.view.project(feat.centre), str(feat.label)))
        for axis, point, radius in feat.holes:
            for p in plots.values():
                if p.view.axis(axis) is None:
                    p.centres.append((p.view.project(point), radius))

    iso = plots.pop(None)
    views = list(plots.values())
    group = _group(model, part)
    # a note per label, with the count of identical features
    counts = Counter(f.label for f in feats)
    texts = {f.label: f.text for f in feats}
    notes = [
        f"{label}  {counts[label]} x {text}" if counts[label] > 1 else f"{label}  {text}"
        for label, text in texts.items()
    ]
    if len(group) > 1:
        notes.insert(0, f"{len(group)} pieces: {group.members()}")
    notes = _wrap(notes)
    layout = Layout([*views, iso], notes=_notes_size(notes))
    size = layout.fit()
    # features whose dimensions crowd at the scale of their view, enlarged;
    # again at the scales the details lead to, until they settle, without
    # those that can't be enlarged enough
    details: list[Plot] = []
    skip: set[tuple[Side, int]] = set()
    for _ in range(DETAIL_ROUNDS):
        found, moved = _details(plots, chosen, skip)
        if [d.label for d in found] == [d.label for d in details]:
            break
        details = found
        _dimension(plots, chosen, rod, moved)
        layout = Layout([*views, *details, iso], notes=_notes_size(notes))
        size = layout.fit()
        small = [d for d in details if d.scale < DETAIL_ENLARGES * d.parent[0].scale]
        skip |= {(d.parent[0].side, n) for d in small for n in d.numbers}
    views += details
    sheet = Sheet(*size)
    _same_weight(views)
    for plot in layout.plots:
        plot.draw(sheet)
    _notes(sheet, notes)
    _title_block(sheet, _part_title(model, part, group), layout.scale)
    return sheet


def _group(model: ResolvedModel, part: ResolvedPart) -> PartGroup:
    return next(g for g in model.groups if any(p is part for p in g.parts))


def _dimension(
    plots: dict[Side | None, Plot],
    chosen: dict[tuple[Side, int], list[Feature]],
    rod: bool,
    moved: set[tuple[Side, int, int]] = frozenset(),
) -> None:
    """The rows of dimensions of a part's views: chains of the features'
    coordinates (but those `moved` to details: side, feature, axis), inside
    the overall dimensions."""
    for plot in plots.values():
        plot.rows = {}
    # chains on the side of the view nearest each feature, one chain per side
    for (side, axis), shown in chosen.items():
        plot = plots[side]
        i, sign = plot.view.axis(axis)
        bounds = [plot.bounds[0][i], plot.bounds[1][i]]
        chains: dict[str, list[float]] = {}
        for feat in shown:
            if (side, feat.number, axis) not in moved:
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


def _details(
    plots: dict[Side | None, Plot],
    chosen: dict[tuple[Side, int], list[Feature]],
    skip: set[tuple[Side, int]] = frozenset(),
) -> tuple[list[Plot], set[tuple[Side, int, int]]]:
    """Details: views of the parts of views around features whose dimensions
    crowd at the scale of their view (a mortise across a thin edge), enlarged.

    A feature's chain of dimensions along an axis crowds when it has a
    dimension shorter than `MIN_SEGMENT` on paper; those chains go to a
    detail of the region around it, in one view showing all of them if
    there is one (a rabbet's width and depth together; features with the same such chains
    sharing one, overlapping regions merged). A chain leaves its view when
    the detail shows the end of the part it is measured from. Features in
    `skip` (side, number) stay in their views. Returns the details and the
    chains they took: side, feature, axis."""
    entries: dict[int, list[tuple[Side, int, list[float]]]] = {}  # side, axis, values
    centres: dict[int, Vec3] = {}
    labels = {f.number: f.label for shown in chosen.values() for f in shown}
    for (side, axis), shown in chosen.items():
        plot = plots[side]
        i, sign = plot.view.axis(axis)
        lo, hi = plot.bounds[0][i], plot.bounds[1][i]
        for feat in shown:
            if (side, feat.number) in skip:
                continue
            values = [v for _, v, _ in feat.coords]
            chain = _unique([lo, hi, *(sign * v for v in values)])
            if min(b - a for a, b in pairwise(chain)) * plot.scale < MIN_SEGMENT:
                entries.setdefault(feat.number, []).append((side, axis, values))
                centres[feat.number] = feat.centre
    # by the view each goes to: chains by drawing axis, and where they come from
    crowded: dict[tuple[Side, int], dict[int, list[float]]] = {}
    origins: dict[tuple[Side, int], dict[int, list[tuple[Side, int, int]]]] = {}
    for number, found_in in entries.items():
        axes = {axis for _, axis, _ in found_in}
        showing = [s for s, _, _ in found_in if all(plots[s].view.axis(a) for a in axes)]
        for side, axis, values in found_in:
            target = showing[0] if showing else side
            i, sign = plots[target].view.axis(axis)
            crowded.setdefault((target, number), {})[i] = [sign * v for v in values]
            origins.setdefault((target, number), {}).setdefault(i, []).append((side, number, axis))

    # one region per side and the same crowded chains
    regions: dict[tuple, list] = {}
    for (side, number), chains in crowded.items():
        key = (side, tuple(sorted((i, tuple(_unique(v))) for i, v in chains.items())))
        regions.setdefault(key, [side, [], chains])[1].append(number)
    found: list[list] = []  # side, window, numbers, chains by axis, their origins
    for side, numbers, chains in regions.values():
        plot = plots[side]
        centre = plot.view.project(centres[numbers[0]])
        window = [list(_window(plot, i, chains.get(i, []), centre[i])) for i in (0, 1)]
        came = {}
        for n in numbers:
            for i, o in origins[(side, n)].items():
                came.setdefault(i, []).extend(o)
        found.append([side, window, numbers, {i: list(v) for i, v in chains.items()}, came])
    merged: list[list] = []
    for region in found:
        for other in merged:
            if other[0] == region[0] and all(
                region[1][i][0] <= other[1][i][1] + 2 * DETAIL_MARGIN
                and other[1][i][0] <= region[1][i][1] + 2 * DETAIL_MARGIN
                for i in (0, 1)
            ):
                for i in (0, 1):
                    other[1][i] = [
                        min(other[1][i][0], region[1][i][0]),
                        max(other[1][i][1], region[1][i][1]),
                    ]
                other[2] += region[2]
                for i, values in region[3].items():
                    other[3].setdefault(i, []).extend(values)
                for i, o in region[4].items():
                    other[4].setdefault(i, []).extend(o)
                break
        else:
            merged.append(region)

    details, moved = [], set()
    for side, ((u0, u1), (v0, v1)), numbers, chains, came in merged:
        parent = plots[side]
        window = ((u0, v0), (u1, v1))
        visible = [c for line in parent.visible for c in _clip(line, window)]
        hidden = [c for line in parent.hidden for c in _clip(line, window)]
        label = f"{parent.label}: {_ranges([labels[n] for n in numbers])}"
        detail = Plot(parent.view, None, label, visible, hidden, window, side=side)
        detail.numbers = sorted(numbers)
        detail.zoom, detail.parent, detail.crop = DETAIL_ZOOM, (parent, ((u0 + u1) / 2, v1)), True
        for i, values in sorted(chains.items()):
            ends = [
                b
                for b in (parent.bounds[0][i], parent.bounds[1][i])
                if window[0][i] <= b <= window[1][i]
            ]
            detail.add_row("below" if i == 0 else "left", ends + values)
            if ends:
                moved |= set(came[i])
        for n in sorted(numbers):
            point = parent.view.project(centres[n])
            if u0 <= point[0] <= u1 and v0 <= point[1] <= v1:
                detail.balloons.append((point, str(labels[n])))
        details.append(detail)
    return details, moved


def _ranges(numbers: list[int]) -> str:
    """Numbers as a list of runs: 1, 3-5, 9."""
    runs: list[list[int]] = []
    for n in sorted(set(numbers)):
        if runs and n == runs[-1][-1] + 1:
            runs[-1].append(n)
        else:
            runs.append([n])
    return ", ".join(
        str(r[0]) if len(r) == 1 else f"{r[0]}, {r[1]}" if len(r) == 2 else f"{r[0]}-{r[-1]}"
        for r in runs
    )


def _window(plot: Plot, i: int, values: list[float], centre: float) -> tuple[float, float]:
    """The extent along drawing axis `i` of a detail around a feature: its
    coordinates there (or its centre), with a margin, to the ends of the
    part when they are near."""
    lo, hi = plot.bounds[0][i], plot.bounds[1][i]
    a, b = min([*values, centre]), max([*values, centre])
    margin = max(DETAIL_MARGIN, (b - a) / 4)
    a, b = a - margin, b + margin
    if a - lo < 2 * margin:
        a = lo
    if hi - b < 2 * margin:
        b = hi
    return max(a, lo), min(b, hi)


def _clip(line: Polyline, window: tuple[Point2, Point2]) -> list[Polyline]:
    """The pieces of a polyline inside a window (Liang-Barsky, per segment)."""
    (x0, y0), (x1, y1) = window
    pieces: list[Polyline] = []
    for (ax, ay), (bx, by) in pairwise(line):
        dx, dy = bx - ax, by - ay
        t0, t1 = 0.0, 1.0
        for p, q in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
            if abs(p) < 1e-12:
                if q < -1e-9:
                    t0, t1 = 1.0, 0.0
            elif p < 0:
                t0 = max(t0, q / p)
            else:
                t1 = min(t1, q / p)
        if t0 > t1:
            continue
        a, b = (ax + t0 * dx, ay + t0 * dy), (ax + t1 * dx, ay + t1 * dy)
        if pieces and math.dist(pieces[-1][-1], a) < 1e-9:
            pieces[-1].append(b)
        else:
            pieces.append([a, b])
    return pieces


def _notes_size(notes: list[str]) -> Point2:
    return max((text_width(n, NOTE) for n in notes), default=0.0), len(notes) * NOTE_LINE


def _iso(
    shape: bd.Shape,
    blank: tuple[Vec3, Vec3],
    rod: bool = False,
    label: str = "isometric",
) -> Plot:
    """An isometric view (from the front right, above) with the overall
    dimensions along its edges, placed in the space the other views leave."""
    visible, _ = ISO.lines(shape)
    lo, hi = blank
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    dims = [((x0, y0, z0), (x1, y0, z0), (0, -1, 0), _format(x1 - x0))]
    if not rod:
        dims.append(((x1, y0, z0), (x1, y1, z0), (1, 0, 0), _format(y1 - y0)))
        dims.append(((x0, y0, z0), (x0, y0, z1), (-1, 0, 0), _format(z1 - z0)))
    plot = Plot(ISO, None, label, visible, [], _bounds(ISO, lo, hi), dims3d=dims)
    plot.flexible = True
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


def _wrap(notes: list[str]) -> list[str]:
    """Notes wrapped to the width left of the title block on an A4 sheet."""
    chars = int((A4[0] - 2 * MARGIN - TITLE_WIDTH - VIEW_GAP) / text_width("x", NOTE))
    return [line for note in notes for line in textwrap.wrap(note, chars, subsequent_indent="    ")]


def _notes(sheet: Sheet, lines: list[str]) -> None:
    """Numbered notes in the bottom left corner, from the top of the strip down."""
    y = MARGIN + len(lines) * NOTE_LINE
    for line in lines:
        sheet.text((MARGIN, y - NOTE_LINE + 1), line, size=NOTE, anchor="start")
        y -= NOTE_LINE


def _plot(part: ResolvedPart, side: Side, shape: bd.Shape) -> Plot:
    view, cell = PART_VIEWS[side]
    visible, hidden = view.lines(shape)
    label = SideRef(part.part, side).name.replace("_", " ")
    if isinstance(part.part, Rod) and side.axis != 0:
        label = "side"
    plot = Plot(view, cell, label, visible, hidden, _bounds(view, *part.blank), side=side)
    if side.axis == 0:
        plot.zoom = END_ZOOM  # an end, small beside the length of the part
    return plot


def _part_title(
    model: ResolvedModel, part: ResolvedPart, group: PartGroup
) -> list[tuple[str, str]]:
    p = part.part
    size = _part_title_size(part)
    material = p.stock.species + (", mirror image" if p.mirror else "")
    return [
        ("part", group.name),
        ("of", model.name),
        ("make", _quantity(group)),
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
    iso = _iso(shape, (lo, hi))

    layout = Layout([*plots.values(), iso])
    sheet = Sheet(*layout.fit())
    _same_weight(list(plots.values()))
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
    # each part numbered as its group
    numbers = {p.part.name: i for i, group in enumerate(model.groups, 1) for p in group.parts}
    for child in apart.children:
        centre = ISO.project(tuple(child.bounding_box().center()))
        blown.balloons.append((centre, str(numbers[child.label])))

    rows = [_part_row(i, group) for i, group in enumerate(model.groups, 1)]
    widths = _column_widths(rows)
    list_width = sum(widths)
    list_height = (len(rows) + 1) * NOTE_LINE
    title = TITLE_ROWS * 6.0
    sheet = Sheet(A4[0], max(A4[1], 3 * MARGIN + list_height + title))
    # not to scale: as large as fits left of the parts list and the title block
    width = sheet.width - 2 * MARGIN - max(list_width, TITLE_WIDTH) - VIEW_GAP
    height = sheet.height - 2 * MARGIN
    (u0, v0), (u1, v1) = blown.bounds
    band = blown.band("left")
    blown.scale = min(
        (width - 2 * band) / (u1 - u0),
        (height - 2 * band - LABEL_GAP - LABEL) / (v1 - v0),
    )
    left = MARGIN + (width - blown.size[0]) / 2
    top = sheet.height - MARGIN - band
    blown.origin = (left - u0 * blown.scale, top - v1 * blown.scale)
    blown.draw(sheet)
    _parts_list(sheet, rows, widths, (sheet.width - MARGIN - list_width, sheet.height - MARGIN))
    shape_box = model.compound().bounding_box()
    _title_block(sheet, _assembly_title(model, tuple(shape_box.min), tuple(shape_box.max)), None)
    return sheet


COVER_TITLE = 12.0  # height of the name on the cover
COVER_INFO = 4.0  # of the lines below the picture


def cover_sheet(model: ResolvedModel, lines: list[tuple[str, str]] = ()) -> Sheet:
    """A cover for the plans: the name, a large isometric view of the whole
    thing (no dimensions, no hidden lines), and below it its overall size,
    parts and materials, then `lines` (e.g. the date)."""
    shape = model.compound()
    box = shape.bounding_box()
    lo, hi = tuple(box.min), tuple(box.max)
    visible, _ = ISO.lines(shape)
    plot = Plot(ISO, None, "", visible, [], _bounds(ISO, lo, hi))
    sheet = Sheet(*A4)
    info = [row for row in _assembly_title(model, lo, hi) if row[0] != "assembly"]
    info += list(lines)
    title_top = sheet.height - 2 * MARGIN
    picture_top = title_top - COVER_TITLE - 2 * MARGIN
    picture_bottom = 2 * MARGIN + len(info) * COVER_INFO * 1.6 + MARGIN
    (u0, v0), (u1, v1) = plot.bounds
    plot.scale = min(
        (sheet.width - 4 * MARGIN) / (u1 - u0), (picture_top - picture_bottom) / (v1 - v0)
    )
    width, height = plot.size
    left = (sheet.width - width) / 2
    bottom = picture_bottom + (picture_top - picture_bottom - height) / 2
    plot.origin = (left - u0 * plot.scale, bottom - v0 * plot.scale)
    weight = "visible" + plot.weight()
    for line in plot.visible:
        sheet.line([plot.at(p) for p in line], weight)

    title = model.name.replace("_", " ")
    sheet.text(
        (2 * MARGIN, title_top - COVER_TITLE),
        title[:1].upper() + title[1:],
        size=COVER_TITLE,
        anchor="start",
        bold=True,
    )
    sheet.line(
        [
            (2 * MARGIN, title_top - COVER_TITLE - 5),
            (sheet.width - 2 * MARGIN, title_top - COVER_TITLE - 5),
        ],
        "frame",
    )
    y = 2 * MARGIN + (len(info) - 1) * COVER_INFO * 1.6
    for key, value in info:
        sheet.text((2 * MARGIN, y), key, size=COVER_INFO * 0.7, anchor="start")
        sheet.text((2 * MARGIN + 25, y), value, size=COVER_INFO, anchor="start")
        y -= COVER_INFO * 1.6
    return sheet


def _assembly_title(model: ResolvedModel, lo: Vec3, hi: Vec3) -> list[tuple[str, str]]:
    width, depth, height = (b - a for a, b in zip(lo, hi, strict=True))
    return [
        ("assembly", model.name),
        ("parts", _parts_count(model)),
        ("overall", f"{_format(width)} x {_format(depth)} x {_format(height)} (W x D x H)"),
        ("material", ", ".join(sorted({p.part.stock.species for p in model.parts}))),
    ]


def _parts_count(model: ResolvedModel) -> str:
    """'21', or with identical parts, '21 (12 different)'."""
    different = len(model.groups)
    return f"{len(model.parts)}" + (
        f" ({different} different)" if different < len(model.parts) else ""
    )


def _quantity(group: PartGroup) -> str:
    """'4', or with mirror images, '4 (2 mirror image)'."""
    mirrored = f" ({len(group.mirrored)} mirror image)" if group.mirrored else ""
    return f"{len(group)}{mirrored}"


def _part_row(number: int, group: PartGroup) -> list[str]:
    part = group.first
    size = _part_title_size(part)
    notes = ["mirror image"] if part.part.mirror else []
    if group.mirrored:
        notes.append(f"{len(group.mirrored)} mirror image")
    species = part.part.stock.species
    return [str(number), group.name, str(len(group)), size, species, ", ".join(notes)]


def _part_title_size(part: ResolvedPart) -> str:
    if isinstance(part.part, Rod):
        return f"ø{part.part.diameter:g} x {part.size[0]:g}"
    return " x ".join(f"{x:g}" for x in part.size)


PARTS_HEADER = ["no.", "part", "qty", "cut size (L x W x T)", "material", ""]


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
