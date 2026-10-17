"""Cuts: material removed from a part, built in the part's frame."""

from dataclasses import dataclass

import build123d as bd

from woodwright.part import Board, SideRef


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
        raise NotImplementedError

    def describe(self) -> str:
        raise NotImplementedError


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
        raise NotImplementedError

    def removal(self) -> bd.Part:
        raise NotImplementedError

    def describe(self) -> str:
        raise NotImplementedError


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
