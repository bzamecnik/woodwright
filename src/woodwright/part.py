"""Parts made from stock, their local frame and their named sides.

A board is described as if it lies flat on the bench, length left to right,
reference face up and reference arris (where the reference face meets the
reference edge) towards the woodworker.

Part frame (mm): the origin lies on the reference arris at the left end,
x runs along the length (grain), y across the width towards the back edge,
z up along the normal of the reference face. The design box of a board is
therefore [0, length] x [0, width] x [-thickness, 0].

A mirrored board is the mirror image of an unmirrored one with the same
features, e.g. the right side of a case against the left one, both with
their reference faces outside and reference edges at the front. Its part
frame is the same, but its ends swap names: its left end lies at x =
length. Joints and cuts on its named sides are then mirrored too.

A rod (round stock) is thought of as a square box with its four long
arrises rounded off: its frame and design box are those of a board as wide
and thick as its diameter, [0, length] x [0, diameter] x [-diameter, 0],
its axis at y = diameter / 2, z = -diameter / 2. Its ends are real sides;
its four long sides are virtual, the tangent planes of the box. They place
the rod (flush with the top of a rail) and give directions for cross holes
and flats, but cuts that need a planar side refuse them.

A board may be laminated: glued up from equal plies, then cut as one. The
plies show as separate solids in the model (the glue lines in the drawings)
and in the cut list.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Literal

import build123d as bd

from woodwright.stock import Stock

if TYPE_CHECKING:
    from woodwright.cuts import Cut

Point = tuple[float, float, float]


class Side(Enum):
    """The six sides of a board, as (axis of the normal, its sign)."""

    TOP_FACE = (2, +1)
    BOTTOM_FACE = (2, -1)
    FRONT_EDGE = (1, -1)
    BACK_EDGE = (1, +1)
    LEFT_END = (0, -1)
    RIGHT_END = (0, +1)

    def __init__(self, axis: int, sign: int) -> None:
        self.axis = axis
        self.sign = sign


class Part:
    """Base class of parts: a named piece of stock with a design length.

    The design box is the part as the user sees it between its joints, e.g. a
    rail from shoulder to shoulder. Joints may extend the blank beyond it.
    With `mirror`, its ends swap names (see the module docs).
    """

    name: str
    stock: Stock
    length: float
    cuts: list[Cut]
    mirror: bool

    @property
    def thickness(self) -> float:
        return self.stock.thickness

    @property
    def box(self) -> tuple[Point, Point]:
        """Min and max corners of the design box in the part frame."""
        raise NotImplementedError

    def blank(self, lo: Point, hi: Point) -> bd.Part:
        """The blank filling the box between `lo` and `hi` (the design box
        with any allowances), in the part frame."""
        raise NotImplementedError

    def is_virtual(self, side: Side) -> bool:
        """Whether a side isn't a real planar side of the part (of a rod)."""
        return False

    def ply_boxes(self, lo: Point, hi: Point) -> list[tuple[Point, Point]]:
        """The boxes of the plies the blank between `lo` and `hi` is glued up from."""
        return [(lo, hi)]

    def side(self, side: Side) -> SideRef:
        """The side named `side`; on a mirrored part the ends are swapped."""
        return SideRef(self, _named(side, self.mirror))

    def arris(self, a: SideRef, b: SideRef) -> ArrisRef:
        """The arris where two adjacent sides of this part meet."""
        return ArrisRef(a, b)

    def cut(self, cut: Cut) -> Cut:
        """Add an explicit cut to this part."""
        self.cuts.append(cut)
        return cut

    @property
    def top_face(self) -> SideRef:
        return self.side(Side.TOP_FACE)

    @property
    def bottom_face(self) -> SideRef:
        return self.side(Side.BOTTOM_FACE)

    @property
    def front_edge(self) -> SideRef:
        return self.side(Side.FRONT_EDGE)

    @property
    def back_edge(self) -> SideRef:
        return self.side(Side.BACK_EDGE)

    @property
    def left_end(self) -> SideRef:
        return self.side(Side.LEFT_END)

    @property
    def right_end(self) -> SideRef:
        return self.side(Side.RIGHT_END)

    @property
    def ref_face(self) -> SideRef:
        return self.top_face

    @property
    def ref_edge(self) -> SideRef:
        return self.front_edge

    @property
    def ref_arris(self) -> ArrisRef:
        return self.arris(self.top_face, self.front_edge)


@dataclass(eq=False)
class Board(Part):
    """A named board with design dimensions; thickness comes from its stock.

    With `plies` > 1, it is laminated from as many equal boards, stacked
    through its thickness (glued face to face, the glue lines showing on its
    edges and ends) or, with `plies_across="width"`, side by side across its
    width (the glue lines on its faces and ends), e.g. a 90 mm square leg
    from two 45 x 90 mm boards.
    """

    name: str
    stock: Stock
    length: float
    width: float
    cuts: list[Cut] = field(default_factory=list)
    mirror: bool = False
    plies: int = 1
    plies_across: Literal["thickness", "width"] = "thickness"

    def __post_init__(self) -> None:
        if self.stock.round:
            raise ValueError(f"{self.name} is a board, but its stock is round: make it a Rod")
        if self.plies < 1:
            raise ValueError(f"{self.name} needs at least one ply")
        if self.plies_across not in ("thickness", "width"):
            raise ValueError(f"{self.name}: plies go across its thickness or its width")

    def ply_boxes(self, lo: Point, hi: Point) -> list[tuple[Point, Point]]:
        axis = 2 if self.plies_across == "thickness" else 1
        step = (hi[axis] - lo[axis]) / self.plies
        boxes = []
        for i in range(self.plies):
            a, b = list(lo), list(hi)
            a[axis] = lo[axis] + i * step
            b[axis] = a[axis] + step
            boxes.append((tuple(a), tuple(b)))
        return boxes

    @property
    def box(self) -> tuple[Point, Point]:
        return (0.0, 0.0, -self.thickness), (self.length, self.width, 0.0)

    def blank(self, lo: Point, hi: Point) -> bd.Part:
        size = [b - a for a, b in zip(lo, hi, strict=True)]
        return bd.Pos(*lo) * bd.Box(*size, align=(bd.Align.MIN,) * 3)


@dataclass(eq=False)
class Rod(Part):
    """A named rod of round stock: a dowel, a peg, a rung, a pole.

    Its frame is that of its bounding box (see the module docs); its long
    sides (`top_face`, `front_edge`, ...) are virtual. Allowances only go on
    its ends.
    """

    name: str
    stock: Stock
    length: float
    cuts: list[Cut] = field(default_factory=list)
    mirror: bool = False

    def __post_init__(self) -> None:
        if not self.stock.round:
            raise ValueError(f"{self.name} is a rod, but its stock is a board: use Stock.rod")

    @property
    def diameter(self) -> float:
        return self.stock.diameter

    @property
    def width(self) -> float:
        return self.diameter

    @property
    def box(self) -> tuple[Point, Point]:
        return (0.0, 0.0, -self.diameter), (self.length, self.diameter, 0.0)

    @property
    def axis(self) -> tuple[float, float]:
        """The y and z coordinates of the rod's axis in its frame."""
        return self.diameter / 2, -self.diameter / 2

    def is_virtual(self, side: Side) -> bool:
        return side.axis != 0

    def blank(self, lo: Point, hi: Point) -> bd.Part:
        y, z = self.axis
        cylinder = bd.Cylinder(
            self.diameter / 2, hi[0] - lo[0], rotation=(0, 90, 0), align=_AXIAL_MIN
        )
        return bd.Pos(lo[0], y, z) * cylinder


@dataclass(frozen=True)
class SideRef:
    """A reference to one side of a part's design box."""

    part: Part
    side: Side

    @property
    def virtual(self) -> bool:
        """Whether the side isn't a real planar side of the part (a long side of a rod)."""
        return self.part.is_virtual(self.side)

    @property
    def axis(self) -> int:
        return self.side.axis

    @property
    def normal(self) -> bd.Vector:
        """Outward unit normal in the part frame."""
        return _unit(self.axis, self.side.sign)

    @property
    def plane(self) -> bd.Plane:
        """Plane of the side in the part frame.

        z is the outward normal. x runs along the length for faces and edges,
        along the width for ends. y follows from the right-hand rule. The
        origin is the corner of the side such that the side covers
        [0, size[0]] x [0, size[1]] in plane coordinates. The plane is the
        same on a mirrored board: x runs from its right end.
        """
        lo, hi = self.part.box
        x_axis, y_axis = self._plane_axes
        x_dir = _unit(x_axis)
        y_dir = self.normal.cross(x_dir)
        origin = [0.0, 0.0, 0.0]
        origin[self.axis] = self.coordinate
        origin[x_axis] = lo[x_axis]
        origin[y_axis] = lo[y_axis] if tuple(y_dir)[y_axis] > 0 else hi[y_axis]
        return bd.Plane(origin=tuple(origin), x_dir=x_dir, z_dir=self.normal)

    @property
    def size(self) -> tuple[float, float]:
        """Extent of the side along the plane's x and y."""
        lo, hi = self.part.box
        x_axis, y_axis = self._plane_axes
        return hi[x_axis] - lo[x_axis], hi[y_axis] - lo[y_axis]

    @property
    def depth(self) -> float:
        """Depth of material behind the side (the part's extent along the normal)."""
        lo, hi = self.part.box
        return hi[self.axis] - lo[self.axis]

    @property
    def coordinate(self) -> float:
        """Coordinate of the side along its axis in the part frame."""
        lo, hi = self.part.box
        return (hi if self.side.sign > 0 else lo)[self.axis]

    @property
    def _plane_axes(self) -> tuple[int, int]:
        # x along the length for faces and edges, along the width for ends
        x_axis = 1 if self.axis == 0 else 0
        return x_axis, 3 - self.axis - x_axis

    @property
    def name(self) -> str:
        """The name of the side, e.g. `left_end` (swapped on a mirrored board)."""
        return _named(self.side, self.part.mirror).name.lower()

    def __str__(self) -> str:
        return f"{self.part.name}.{self.name}"


@dataclass(frozen=True)
class ArrisRef:
    """The geometric edge where two adjacent sides of a part meet."""

    a: SideRef
    b: SideRef

    def __post_init__(self) -> None:
        if self.a.part is not self.b.part or self.a.axis == self.b.axis:
            raise ValueError(f"{self.a} and {self.b} are not adjacent sides")

    @property
    def endpoints(self) -> tuple[bd.Vector, bd.Vector]:
        """The two ends of the arris in the part frame, in increasing coordinate."""
        lo, hi = self.a.part.box
        along = 3 - self.a.axis - self.b.axis
        start = [0.0, 0.0, 0.0]
        start[self.a.axis] = self.a.coordinate
        start[self.b.axis] = self.b.coordinate
        end = list(start)
        start[along], end[along] = lo[along], hi[along]
        return bd.Vector(*start), bd.Vector(*end)

    def __str__(self) -> str:
        return f"{self.a.part.name}.{self.a.name}_{self.b.name}_arris"


# A cylinder lying along x, from x = 0, centered on its axis.
_AXIAL_MIN = (bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)


def _named(side: Side, mirror: bool) -> Side:
    """The side named `side` on a part, or the other way round (it's symmetric)."""
    if not mirror or side.axis != 0:
        return side
    return Side.RIGHT_END if side is Side.LEFT_END else Side.LEFT_END


def _unit(axis: int, sign: int = 1) -> bd.Vector:
    coords = [0.0, 0.0, 0.0]
    coords[axis] = float(sign)
    return bd.Vector(*coords)
