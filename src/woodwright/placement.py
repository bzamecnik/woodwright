"""Placing one part relative to another by mating their sides."""

from dataclasses import dataclass

import build123d as bd

from woodwright.part import SideRef


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
    raise NotImplementedError
