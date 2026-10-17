"""Placing one part relative to another by mating their sides."""

from dataclasses import dataclass

import build123d as bd

from woodwright.part import ArrisRef, SideRef


@dataclass(frozen=True)
class Centered:
    """The mating arrises are centered on each other."""


@dataclass(frozen=True)
class Offset:
    """The second arris starts `distance` along the first one from its start."""

    distance: float


Position = Centered | Offset

CENTERED = Centered()


def centered() -> Centered:
    return CENTERED


def offset(distance: float) -> Offset:
    return Offset(distance)


def mate(
    a: SideRef,
    b: SideRef,
    flush: tuple[SideRef, SideRef],
    position: Position = CENTERED,
) -> bd.Location:
    """Location of `b.part` in the frame of `a.part`.

    Side `b` lies against side `a` (opposite normals). The sides `flush[0]` (of
    `a.part`, adjacent to `a`) and `flush[1]` (of `b.part`, adjacent to `b`) are
    coplanar and face the same way. Along the arris where each mating side
    meets its flush side, the parts are positioned by `position`.
    """
    frame_a = _mating_frame(a, flush[0], position, inward=False)
    frame_b = _mating_frame(b, flush[1], position, inward=True)
    return frame_a * frame_b.inverse()


def _mating_frame(side: SideRef, flush: SideRef, position: Position, inward: bool) -> bd.Location:
    """Frame on the arris of `side` and `flush`, in the part frame.

    z is the normal of the mating side (reversed for the part being placed, so
    that both frames coincide when the sides touch), y is the normal of the
    flush side and x runs along the arris.
    """
    if flush.part is not side.part:
        raise ValueError(f"{flush} is not a side of {side.part.name}")
    start, end = ArrisRef(side, flush).endpoints
    z_dir = -side.normal if inward else side.normal
    x_dir = flush.normal.cross(z_dir)
    if (end - start).dot(x_dir) < 0:
        start, end = end, start
    match position:
        case Centered():
            origin = (start + end) * 0.5
        case Offset(distance):
            # Only the first part's frame is offset; the second one starts at its arris.
            origin = start if inward else start + x_dir * distance
    return bd.Location(bd.Plane(origin, x_dir=x_dir, z_dir=z_dir))
