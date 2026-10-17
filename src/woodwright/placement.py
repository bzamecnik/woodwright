"""Placing one part relative to another by mating their sides, and orienting the root."""

from dataclasses import dataclass

import build123d as bd

from woodwright.part import ArrisRef, Board, Point, SideRef

# Directions in the assembly, as seen by a viewer in front of it: X to the
# right, Y away from the viewer (to the back), Z up.
Direction = tuple[float, float, float]
RIGHT: Direction = (1, 0, 0)
LEFT: Direction = (-1, 0, 0)
BACK: Direction = (0, 1, 0)
FRONT: Direction = (0, -1, 0)
UP: Direction = (0, 0, 1)
DOWN: Direction = (0, 0, -1)


@dataclass(frozen=True)
class Centered:
    """The mating arrises are centered on each other."""


@dataclass(frozen=True)
class Offset:
    """A distance between the two parts along their mating arrises.

    With `ref`, a side of the first part at one end of its arris, the
    distance is from `ref` to the side of the second part facing the same
    way, measured inwards. Without, it is from the start of the first arris
    (by the right-hand rule) to the start of the second one.
    """

    distance: float
    ref: SideRef | None = None


Position = Centered | Offset

CENTERED = Centered()
FLUSH = Offset(0)


def centered() -> Centered:
    return CENTERED


def offset(distance: float, ref: SideRef | None = None) -> Offset:
    return Offset(distance, ref)


def flush_with(ref: SideRef) -> Offset:
    """The second part is flush with the side `ref` of the first part."""
    return Offset(0, ref)


def mate(
    a: SideRef,
    b: SideRef,
    flush: tuple[SideRef, SideRef],
    position: Position = CENTERED,
    across: Position = FLUSH,
    gap: float = 0.0,
) -> bd.Location:
    """Location of `b.part` in the frame of `a.part`.

    Side `b` lies against side `a` (opposite normals). The sides `flush[0]` (of
    `a.part`, adjacent to `a`) and `flush[1]` (of `b.part`, adjacent to `b`)
    face the same way. Along the arris where each mating side meets its
    flush side, the parts are positioned by `position`. Across it, `across`
    sets `flush[1]` back from `flush[0]` by a distance (coplanar by default),
    or centers the parts on each other. With `gap`, side `b` lies that far
    from side `a`; a negative gap makes the parts overlap (e.g. at a mitre).
    """
    start_a, end_a, x_a, z_a = _arris(a, flush[0], inward=False)
    start_b, end_b, x_b, z_b = _arris(b, flush[1], inward=True)

    match position:
        case Centered():
            origin_a, origin_b = (start_a + end_a) * 0.5, (start_b + end_b) * 0.5
        case Offset(distance, None):
            origin_a, origin_b = start_a + x_a * distance, start_b
        case Offset(distance, ref):
            along = 3 - a.axis - flush[0].axis
            if ref.part is not a.part or ref.axis != along:
                raise ValueError(f"{ref} is not a side at an end of the arris of {a}")
            if ref.normal.dot(x_a) < 0:
                origin_a = start_a + x_a * distance
            else:
                origin_a = end_a - x_a * (distance + (end_b - start_b).length)
            origin_b = start_b

    match across:
        case Centered():
            origin_a -= flush[0].normal * (flush[0].depth / 2)
            origin_b -= flush[1].normal * (flush[1].depth / 2)
        case Offset(distance, None):
            origin_a -= flush[0].normal * distance
        case Offset():
            raise ValueError("an offset across the arris is measured from the flush side")

    origin_a += a.normal * gap
    frame_a = bd.Location(bd.Plane(origin_a, x_dir=x_a, z_dir=z_a))
    frame_b = bd.Location(bd.Plane(origin_b, x_dir=x_b, z_dir=z_b))
    return frame_a * frame_b.inverse()


def _arris(
    side: SideRef, flush: SideRef, inward: bool
) -> tuple[bd.Vector, bd.Vector, bd.Vector, bd.Vector]:
    """Start, end and the x and z directions of the mating frame on an arris.

    z is the normal of the mating side (reversed for the part being placed, so
    that both frames coincide when the sides touch), y is the normal of the
    flush side and x runs along the arris, from its start to its end.
    """
    if flush.part is not side.part:
        raise ValueError(f"{flush} is not a side of {side.part.name}")
    start, end = ArrisRef(side, flush).endpoints
    z_dir = -side.normal if inward else side.normal
    x_dir = flush.normal.cross(z_dir)
    if (end - start).dot(x_dir) < 0:
        start, end = end, start
    return start, end, x_dir, z_dir


@dataclass(frozen=True)
class Orientation:
    """Which way two sides of a part face, and where its design box lies.

    `facing` maps the names of two adjacent sides of the part (e.g.
    `right_end`, `ref_face`) to the directions they face. The design box
    is moved so that its lowest corner lies at `at`.
    """

    facing: dict[str, Direction]
    at: Point = (0.0, 0.0, 0.0)

    def __post_init__(self) -> None:
        if len(self.facing) != 2:
            raise ValueError("orient a part by the directions of exactly two of its sides")

    def location(self, part: Board) -> bd.Location:
        """Location of `part` in the assembly."""
        (a, da), (b, db) = self.facing.items()
        side_a, side_b = getattr(part, a), getattr(part, b)
        if not isinstance(side_a, SideRef) or not isinstance(side_b, SideRef):
            raise ValueError(f"{a} and {b} must name sides of {part.name}")
        if side_a.axis == side_b.axis:
            raise ValueError(f"{side_a} and {side_b} are not adjacent sides")
        da, db = bd.Vector(da).normalized(), bd.Vector(db).normalized()
        if abs(da.dot(db)) > 1e-6:
            raise ValueError(f"{side_a} and {side_b} must face perpendicular directions")
        na, nb = side_a.normal, side_b.normal
        world = bd.Location(bd.Plane((0, 0, 0), x_dir=da, z_dir=da.cross(db)))
        local = bd.Location(bd.Plane((0, 0, 0), x_dir=na, z_dir=na.cross(nb)))
        rotation = world * local.inverse()
        lo, hi = part.box
        corners = [
            (rotation * bd.Location((x, y, z))).position
            for x in (lo[0], hi[0])
            for y in (lo[1], hi[1])
            for z in (lo[2], hi[2])
        ]
        lowest = bd.Vector(*(min(tuple(c)[axis] for c in corners) for axis in range(3)))
        return bd.Location(tuple(bd.Vector(self.at) - lowest)) * rotation


def orient(at: Point = (0.0, 0.0, 0.0), **facing: Direction) -> Orientation:
    """Orient the root part of an assembly by the directions two of its sides face.

    E.g. a stile standing up, its back edge to the right:
    `orient(right_end=UP, back_edge=RIGHT)`. Its design box lies in the
    positive octant from `at`.
    """
    return Orientation(facing, at)
