"""Joints: relations between two parts that place them and cut both."""

import functools
import operator
from dataclasses import dataclass, replace
from typing import Self

import build123d as bd

from woodwright import rules
from woodwright.cuts import Cut, Mortise, ShapeCut, Tenon
from woodwright.part import Board, Side, SideRef
from woodwright.placement import CENTERED, Position, mate, offset


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
        return replace(
            self,
            tenon_thickness=self.tenon_thickness
            or rules.tenon_thickness(self.tenon.part.thickness),
            tenon_length=self.tenon_length or rules.tenon_length(self.mortise.depth),
        )

    def allowances(self) -> list[Allowance]:
        return [Allowance(self.tenon, self._tenon_cut().length)]

    def placement(self) -> bd.Location:
        flush = (self.mortise.part.ref_face, self.tenon.part.ref_face)
        return mate(self.mortise, self.tenon, flush=flush, position=self.position)

    def cuts(self, placement: bd.Location) -> list[Cut]:
        tenon = self._tenon_cut()
        # The mortise goes where the tenon is, seen from the mortised part.
        box = (placement * tenon.tenon()).bounding_box()
        plane = self.mortise.plane
        lo, hi = plane.to_local_coords(box.min), plane.to_local_coords(box.max)
        (u0, u1), (v0, v1) = sorted((lo.X, hi.X)), sorted((lo.Y, hi.Y))
        mortise = Mortise(
            self.mortise,
            start=u0,
            length=u1 - u0,
            offset=v0,
            width=v1 - v0,
            depth=-min(lo.Z, hi.Z) + self.clearance,
        )
        return [mortise, tenon]

    def _tenon_cut(self) -> Tenon:
        if self.tenon_thickness is None or self.tenon_length is None:
            raise ValueError("unset joint parameters, call with_defaults() first")
        return Tenon(
            self.tenon,
            length=self.tenon_length,
            thickness=self.tenon_thickness,
            width=self.tenon.size[0] - 2 * self.shoulder,
        )


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

    def __post_init__(self) -> None:
        # TODO: other combinations of ends, once mating can express them simply.
        if self.pins.side is not Side.RIGHT_END or self.tails.side is not Side.LEFT_END:
            raise NotImplementedError("only pins on a right end and tails on a left end")
        if self.pins.part.width != self.tails.part.width:
            raise ValueError("dovetailed boards must have the same width")

    def allowances(self) -> list[Allowance]:
        # Both boards reach through each other.
        return [
            Allowance(self.tails, self.pins.part.thickness),
            Allowance(self.pins, self.tails.part.thickness),
        ]

    def placement(self) -> bd.Location:
        # The tail board's end lies against the inside face of the pin board,
        # its bottom face level with the end of the pin board's design box.
        pins, tails = self.parts()
        return mate(
            pins.bottom_face,
            self.tails,
            flush=(pins.ref_edge, tails.ref_edge),
            position=offset(pins.length),
        )

    def cuts(self, placement: bd.Location) -> list[Cut]:
        pins, tails = self.parts()
        # Corner block where the boards overlap, in the pin board's frame.
        block = bd.Pos(pins.length, 0, -pins.thickness) * bd.Box(
            tails.thickness, pins.width, pins.thickness, align=(bd.Align.MIN,) * 3
        )
        # Pin profiles are drawn across the width (x) and the thickness (y) of
        # the pin board and extruded along its length, through the tail board.
        profile_plane = bd.Plane((pins.length, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
        pin_solids = [
            bd.extrude(profile_plane * bd.Polygon(*points), amount=tails.thickness)
            for points in self._pin_profiles()
        ]
        pin_solid = functools.reduce(operator.add, pin_solids)
        return [
            ShapeCut(pins, block - pin_solid, f"sockets for {self.tail_count} dovetails"),
            ShapeCut(
                tails,
                placement.inverse() * pin_solid,
                f"{self.tail_count} dovetails, slope 1:{self.slope:g}",
            ),
        ]

    def _pin_profiles(self) -> list[list[tuple[float, float]]]:
        """Outlines of the pins (incl. half pins) as (across the width, along the normal).

        Pins are narrowest on the outside face of the pin board (y = 0) and
        widest on its inside face (y = -thickness). Along the width the joint
        is laid out as: half pin | tail | pin | tail | ... | pin | tail | half pin
        """
        t, width = self.pins.part.thickness, self.pins.part.width
        flare = t / self.slope  # how far each sloped flank leans over the thickness
        n = self.tail_count
        tail_wide = (width - 2 * self.half_pin_width - (n - 1) * self.pin_width) / n
        if tail_wide - 2 * flare <= 0:
            raise ValueError("tails too narrow for this slope and pin width")

        u = self.half_pin_width
        profiles = [[(0, 0), (0, -t), (u + flare, -t), (u, 0)]]
        for _ in range(n - 1):
            u0 = u + tail_wide
            u1 = u0 + self.pin_width
            profiles.append([(u0, 0), (u0 - flare, -t), (u1 + flare, -t), (u1, 0)])
            u = u1
        u0 = u + tail_wide
        profiles.append([(u0, 0), (u0 - flare, -t), (width, -t), (width, 0)])
        return profiles
