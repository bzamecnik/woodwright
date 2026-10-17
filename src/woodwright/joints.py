"""Joints: relations between two parts that place them and cut both.

Most joints put one part (or a tenon on it) into a socket cut into the other
(`Housing`): the socket is derived from where the inserted part lands, so
the two fit by construction, and the cut list names it by its shape (dado,
rabbet, groove, mortise, ...).
"""

import functools
import operator
from dataclasses import dataclass, replace
from typing import Self

import build123d as bd

from woodwright import rules
from woodwright.cuts import INF, Allowance, Cut, Pocket, Range, ShapeCut, Tenon, Tongue
from woodwright.part import Board, Side, SideRef
from woodwright.placement import CENTERED, FLUSH, Position, mate, offset

__all__ = [
    "Allowance",
    "Bridle",
    "Butt",
    "DadoJoint",
    "GrooveJoint",
    "HalfLap",
    "Housing",
    "Joint",
    "MortiseTenon",
    "RabbetJoint",
    "ThroughDovetail",
    "TongueAndGroove",
]

_EPS = 1e-6


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


def default_flush(a: SideRef, b: SideRef) -> tuple[SideRef, SideRef]:
    """The sides kept flush by default when side `b` mates with side `a`.

    The reference faces, unless one of the mating sides is a face: then the
    reference edges (or the reference face for a mating edge).
    """
    if a.axis != 2 and b.axis != 2:
        return a.part.ref_face, b.part.ref_face

    def pick(side: SideRef) -> SideRef:
        return side.part.ref_face if side.axis == 1 else side.part.ref_edge

    return pick(a), pick(b)


@dataclass
class Butt(Joint):
    """Side `b` glued against side `a`, without any cuts.

    `flush` are the sides kept facing the same way (by default the reference
    faces, or the reference edges for a face); see `mate` for `position` and
    `across`.
    """

    a: SideRef
    b: SideRef
    position: Position = CENTERED
    across: Position = FLUSH
    flush: tuple[SideRef, SideRef] | None = None

    def parts(self) -> tuple[Board, Board]:
        return self.a.part, self.b.part

    def placement(self) -> bd.Location:
        flush = self.flush or default_flush(self.a, self.b)
        return mate(self.a, self.b, flush=flush, position=self.position, across=self.across)


class Housing(Joint):
    """A side of part b goes into a socket cut into a side of part a.

    Part b reaches beyond its design box into part a (an allowance), either
    with its whole cross-section or with a tenon. The socket is cut where it
    lands, with `clearance` at the bottom if it doesn't go through.
    With `through`, the socket runs out of part a at both ends of the mating
    arris, e.g. a groove along the whole edge. Subclasses give the sides, the
    depth and the tenon, and are dataclasses with the fields `position`,
    `across`, `flush` and `clearance` (and `through`, if it applies).
    """

    position: Position
    across: Position
    flush: tuple[SideRef, SideRef] | None
    clearance: float
    through: bool = False  # the socket runs the whole length of part a along the arris

    def sides(self) -> tuple[SideRef, SideRef]:
        """The side the socket is cut into and the side going into it."""
        raise NotImplementedError

    def reach(self) -> float:
        """How far part b reaches into part a."""
        raise NotImplementedError

    def tenon_cut(self) -> Tenon | None:
        """The tenon on part b, or None when its whole cross-section goes in."""
        return None

    def parts(self) -> tuple[Board, Board]:
        socket, insert = self.sides()
        return socket.part, insert.part

    def allowances(self) -> list[Allowance]:
        return [Allowance(self.sides()[1], self.reach())]

    def default_flush(self) -> tuple[SideRef, SideRef]:
        return default_flush(*self.sides())

    def placement(self) -> bd.Location:
        socket, insert = self.sides()
        flush = self.flush or self.default_flush()
        return mate(socket, insert, flush=flush, position=self.position, across=self.across)

    def cuts(self, placement: bd.Location) -> list[Cut]:
        socket, insert = self.sides()
        tenon = self.tenon_cut()
        if tenon is None:
            lo, hi = insert.part.box
            box = [(lo[axis], hi[axis]) for axis in range(3)]
            c, d = insert.coordinate, self.reach()
            box[insert.axis] = (c, c + d) if insert.side.sign > 0 else (c - d, c)
            inserted = (box[0], box[1], box[2])
        else:
            inserted = tenon.tenon_box()
        pocket = Pocket(socket, self.socket_box(placement, inserted))
        return [pocket] if tenon is None else [pocket, tenon]

    def socket_box(
        self, placement: bd.Location, inserted: tuple[Range, Range, Range]
    ) -> tuple[Range, Range, Range]:
        """Ranges of the socket in part a, for a box of part b given in its frame."""
        socket = self.sides()[0]
        box = list(_socket(socket, placement, inserted, self.clearance))
        if self.through:
            along = 3 - socket.axis - (self.flush or self.default_flush())[0].axis
            box[along] = (-INF, INF)
        return box[0], box[1], box[2]


def _require[T](value: T | None) -> T:
    if value is None:
        raise ValueError("unset joint parameters, call with_defaults() first")
    return value


def _socket(
    side: SideRef, placement: bd.Location, inserted: tuple[Range, Range, Range], clearance: float
) -> tuple[Range, Range, Range]:
    """Ranges of the socket in part a for a box of part b, open where it runs out of part a."""
    corners = [
        (placement * bd.Location((x, y, z))).position
        for x in inserted[0]
        for y in inserted[1]
        for z in inserted[2]
    ]
    lo, hi = side.part.box
    ranges = []
    for axis in range(3):
        a = min(tuple(p)[axis] for p in corners)
        b = max(tuple(p)[axis] for p in corners)
        a = -INF if a <= lo[axis] + _EPS else a
        b = INF if b >= hi[axis] - _EPS else b
        # Clearance at the bottom of the socket, if it doesn't go through.
        if axis == side.axis:
            if side.side.sign > 0 and a != -INF:
                a -= clearance
            elif side.side.sign < 0 and b != INF:
                b += clearance
        ranges.append((a, b))
    return ranges[0], ranges[1], ranges[2]


@dataclass
class DadoJoint(Housing):
    """An end (or an edge) of part b housed in a dado in a face (or an edge) of part a.

    Part b's design length stops at the face of part a; the dado depth is
    added to it. By default the reference edges are flush and b is centered
    along a; give `position` e.g. as `offset(100, ref=a.left_end)`.
    """

    dado: SideRef
    end: SideRef
    depth: float | None = None
    position: Position = CENTERED
    across: Position = FLUSH
    flush: tuple[SideRef, SideRef] | None = None
    clearance: float = 0.0

    def sides(self) -> tuple[SideRef, SideRef]:
        return self.dado, self.end

    def with_defaults(self) -> Self:
        return replace(self, depth=self.depth or rules.dado_depth(self.dado.depth))

    def reach(self) -> float:
        return _require(self.depth)


@dataclass
class RabbetJoint(Housing):
    """An end of part b in a rabbet cut into side `rabbet` of part a, at its side `at`.

    E.g. the top of a carcase in rabbets at the top ends of the sides. The
    reference face of part b is flush with `at`; along the arris b is
    centered (or as given by `position`).
    """

    rabbet: SideRef
    end: SideRef
    at: SideRef
    depth: float | None = None
    position: Position = CENTERED
    across: Position = FLUSH
    flush: tuple[SideRef, SideRef] | None = None
    clearance: float = 0.0

    def sides(self) -> tuple[SideRef, SideRef]:
        return self.rabbet, self.end

    def default_flush(self) -> tuple[SideRef, SideRef]:
        return self.at, self.end.part.ref_face

    def with_defaults(self) -> Self:
        return replace(self, depth=self.depth or rules.rabbet_depth(self.rabbet.depth))

    def reach(self) -> float:
        return _require(self.depth)


@dataclass
class GrooveJoint(Housing):
    """An edge of part b (e.g. a panel) in a groove in a side of part a (e.g. a rail).

    By default part b is centered across the thickness of part a and the
    groove runs through the whole length of part a, as when cut on a table saw.
    """

    groove: SideRef
    edge: SideRef
    depth: float | None = None
    through: bool = True  # the groove runs the whole length of part a
    position: Position = CENTERED
    across: Position = CENTERED
    flush: tuple[SideRef, SideRef] | None = None
    clearance: float = 0.0

    def sides(self) -> tuple[SideRef, SideRef]:
        return self.groove, self.edge

    def with_defaults(self) -> Self:
        return replace(self, depth=self.depth or rules.groove_depth(self.groove.part.thickness))

    def reach(self) -> float:
        return _require(self.depth)


@dataclass
class TongueAndGroove(Housing):
    """A tongue along an edge of part b in a groove along a side of part a.

    The boards' design widths are their visible faces; the tongue is added.
    """

    tongue: SideRef
    groove: SideRef
    tongue_thickness: float | None = None
    tongue_length: float | None = None
    through: bool = True  # the groove runs the whole length of part a
    position: Position = CENTERED
    across: Position = FLUSH
    flush: tuple[SideRef, SideRef] | None = None
    clearance: float = 0.0

    def sides(self) -> tuple[SideRef, SideRef]:
        return self.groove, self.tongue

    def with_defaults(self) -> Self:
        thickness = self.tongue.part.thickness
        return replace(
            self,
            tongue_thickness=self.tongue_thickness or rules.tenon_thickness(thickness),
            tongue_length=self.tongue_length or rules.groove_depth(thickness),
        )

    def reach(self) -> float:
        return _require(self.tongue_length)

    def tenon_cut(self) -> Tenon:
        return Tongue(self.tongue, length=self.reach(), thickness=_require(self.tongue_thickness))


@dataclass
class MortiseTenon(Housing):
    """A tenon on an end of one part, in a mortise in a side of the other.

    The reference faces of both parts are flush (see `across` to change
    that). The tenon has a `shoulder` on both edges and is centered across
    the thickness unless `tenon_offset` (from the reference face) is given.
    The mortise is cut where the tenon goes, with some clearance at its
    bottom; a tenon as long as the mortised part is deep goes through.
    """

    tenon: SideRef
    mortise: SideRef
    position: Position = CENTERED
    tenon_thickness: float | None = None
    tenon_length: float | None = None
    shoulder: float = 5.0  # on both edges of the tenoned part
    clearance: float = 2.0  # extra mortise depth
    tenon_offset: float | None = None
    across: Position = FLUSH
    flush: tuple[SideRef, SideRef] | None = None

    def sides(self) -> tuple[SideRef, SideRef]:
        return self.mortise, self.tenon

    def with_defaults(self) -> Self:
        return replace(
            self,
            tenon_thickness=self.tenon_thickness
            or rules.tenon_thickness(self.tenon.part.thickness),
            tenon_length=self.tenon_length or rules.tenon_length(self.mortise.depth),
        )

    def reach(self) -> float:
        return _require(self.tenon_length)

    def tenon_cut(self) -> Tenon:
        return Tenon(
            self.tenon,
            length=self.reach(),
            thickness=_require(self.tenon_thickness),
            width=self.tenon.size[0] - 2 * self.shoulder,
            thickness_offset=self.tenon_offset,
        )


@dataclass
class Bridle(Housing):
    """A tenon over the whole width of an end of part b, through a slot in part a.

    For an L-shaped corner the slot is at an end of part a, e.g. with
    `position=flush_with(a.left_end)`; it then is a slot mortise. The tenon
    is centered across the thickness unless `tenon_offset` is given.
    """

    tenon: SideRef
    slot: SideRef
    position: Position = CENTERED
    tenon_thickness: float | None = None
    tenon_offset: float | None = None
    across: Position = FLUSH
    flush: tuple[SideRef, SideRef] | None = None
    clearance: float = 0.0

    def sides(self) -> tuple[SideRef, SideRef]:
        return self.slot, self.tenon

    def with_defaults(self) -> Self:
        thickness = self.tenon_thickness or rules.tenon_thickness(self.tenon.part.thickness)
        return replace(self, tenon_thickness=thickness)

    def reach(self) -> float:
        return self.slot.depth

    def tenon_cut(self) -> Tenon:
        return Tenon(
            self.tenon,
            length=self.reach(),
            thickness=_require(self.tenon_thickness),
            thickness_offset=self.tenon_offset,
        )


@dataclass
class HalfLap(Housing):
    """An end of part b lapped over (or under) part a, both cut to half thickness.

    Part b gets a lap as long as part a is wide, part a a dado (or an end
    rabbet at a corner) where it lands. With `over`, part b keeps the half at
    its reference face and lies over part a; by default it lies under it, so
    the reference face of part a stays whole.
    """

    lap: SideRef
    socket: SideRef
    position: Position = CENTERED
    lap_thickness: float | None = None
    over: bool = False
    across: Position = FLUSH
    flush: tuple[SideRef, SideRef] | None = None
    clearance: float = 0.0

    def sides(self) -> tuple[SideRef, SideRef]:
        return self.socket, self.lap

    def with_defaults(self) -> Self:
        thickness = self.lap_thickness or rules.lap_thickness(self.lap.part.thickness)
        return replace(self, lap_thickness=thickness)

    def reach(self) -> float:
        return self.socket.depth

    def tenon_cut(self) -> Tenon:
        thickness = _require(self.lap_thickness)
        offset = 0 if self.over else self.lap.part.thickness - thickness
        return Tenon(self.lap, length=self.reach(), thickness=thickness, thickness_offset=offset)


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
