"""Joints: relations between two parts that place them and cut both."""

from dataclasses import dataclass
from typing import Self

import build123d as bd

from woodwright.cuts import Cut
from woodwright.part import Board, SideRef
from woodwright.placement import CENTERED, Position


@dataclass(frozen=True)
class Allowance:
    """Extension of a part's blank beyond its design box at one side."""

    side: SideRef
    amount: float


class Joint:
    """Base class of joints between two parts.

    `placement()` gives the location of `parts()[1]` in the frame of
    `parts()[0]`. Cuts are produced once the placement is known, so that
    joints defined in a shared region can map geometry between the parts.
    """

    def parts(self) -> tuple[Board, Board]:
        raise NotImplementedError

    def with_defaults(self) -> Self:
        """A copy with every unset parameter filled in from the rules."""
        return self

    def allowances(self) -> list[Allowance]:
        return []

    def placement(self) -> bd.Location:
        raise NotImplementedError

    def cuts(self, placement: bd.Location) -> list[Cut]:
        return []


@dataclass
class MortiseTenon(Joint):
    """A tenon on an end of one part, in a mortise in a side of the other.

    The reference faces of both parts are flush. The mortise is cut where
    the tenon goes, with some clearance at its bottom.
    """

    tenon: SideRef
    mortise: SideRef
    position: Position = CENTERED
    tenon_thickness: float | None = None
    tenon_length: float | None = None
    shoulder: float = 5.0  # on both edges of the tenoned part
    clearance: float = 2.0  # extra mortise depth

    def parts(self) -> tuple[Board, Board]:
        return self.mortise.part, self.tenon.part

    def with_defaults(self) -> Self:
        raise NotImplementedError

    def allowances(self) -> list[Allowance]:
        raise NotImplementedError

    def placement(self) -> bd.Location:
        raise NotImplementedError

    def cuts(self, placement: bd.Location) -> list[Cut]:
        raise NotImplementedError


@dataclass
class ThroughDovetail(Joint):
    """Through dovetails at a corner of two boards of equal width.

    The tails are cut on the end of one board, the pins on the end of the
    other. Both boards reach through each other, so each gets an allowance of
    the other's thickness. Reference faces are outside, reference edges flush.
    The geometry is built once in the frame of the pin board and split.
    """

    tails: SideRef
    pins: SideRef
    tail_count: int = 4
    slope: float = 7.0  # 1:slope, between 1:6 (softwood) and 1:8 (hardwood)
    pin_width: float = 8.0  # narrowest, on the outside of the pin board
    half_pin_width: float = 10.0

    def parts(self) -> tuple[Board, Board]:
        return self.pins.part, self.tails.part

    def allowances(self) -> list[Allowance]:
        raise NotImplementedError

    def placement(self) -> bd.Location:
        raise NotImplementedError

    def cuts(self, placement: bd.Location) -> list[Cut]:
        raise NotImplementedError
