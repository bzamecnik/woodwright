"""Cuts: material removed from a part, built in the part's frame."""

from dataclasses import dataclass

import build123d as bd

from woodwright.part import Board, SideRef

_MIN = (bd.Align.MIN, bd.Align.MIN, bd.Align.MIN)


class Cut:
    """Base class of cuts. Most cuts are made into one side of a part."""

    side: SideRef

    @property
    def part(self) -> Board:
        return self.side.part

    def removal(self) -> bd.Part:
        """The removed volume in the part frame."""
        raise NotImplementedError

    def describe(self) -> str:
        return type(self).__name__


@dataclass
class Mortise(Cut):
    """A rectangular pocket into a side, in the side's plane coordinates."""

    side: SideRef
    start: float  # along the side's x
    length: float
    offset: float  # along the side's y
    width: float
    depth: float

    def removal(self) -> bd.Part:
        return side_box(
            self.side, self.start, self.offset, -self.depth, self.length, self.width, self.depth
        )

    def describe(self) -> str:
        return f"mortise {self.length:g} x {self.width:g} mm, {self.depth:g} deep, in {self.side}"


@dataclass
class Tenon(Cut):
    """Shoulders and cheeks cut beyond a side (usually an end), leaving a tenon.

    The side is the shoulder plane; the material beyond it comes from an
    allowance. The tenon is centered on the side unless offsets are given.
    """

    side: SideRef
    length: float
    thickness: float  # along the side's y
    width: float  # along the side's x
    width_offset: float | None = None
    thickness_offset: float | None = None

    def tenon(self) -> bd.Part:
        """The tenon itself, in the part frame."""
        u, v = self.side.size
        width_offset = (u - self.width) / 2 if self.width_offset is None else self.width_offset
        thickness_offset = (
            (v - self.thickness) / 2 if self.thickness_offset is None else self.thickness_offset
        )
        return side_box(
            self.side, width_offset, thickness_offset, 0, self.width, self.thickness, self.length
        )

    def removal(self) -> bd.Part:
        u, v = self.side.size
        return side_box(self.side, 0, 0, 0, u, v, self.length) - self.tenon()

    def describe(self) -> str:
        return f"tenon {self.width:g} x {self.thickness:g} mm, {self.length:g} long, on {self.side}"


@dataclass
class ShapeCut(Cut):
    """An arbitrary build123d solid removed from a part, given in its frame."""

    target: Board
    shape: bd.Part
    name: str = "custom cut"

    @property
    def part(self) -> Board:
        return self.target

    def removal(self) -> bd.Part:
        return self.shape

    def describe(self) -> str:
        return self.name


def side_box(
    side: SideRef, u: float, v: float, w: float, du: float, dv: float, dw: float
) -> bd.Part:
    """A box in the side's plane coordinates, from corner (u, v, w) with sizes (du, dv, dw).

    w is along the outward normal: negative into the part, positive beyond it.
    """
    return bd.Location(side.plane) * bd.Pos(u, v, w) * bd.Box(du, dv, dw, align=_MIN)
