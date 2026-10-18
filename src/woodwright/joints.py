"""Joints: relations between two parts that place them and cut both.

Most joints put one part (or a tenon on it) into a socket cut into the other
(`Housing`): the socket is derived from where the inserted part lands, so
the two fit by construction, and the cut list names it by its shape (dado,
rabbet, groove, mortise, ...).
"""

import functools
import math
import operator
from dataclasses import dataclass, fields, replace
from typing import Self

import build123d as bd

from woodwright import rules
from woodwright.cuts import (
    INF,
    Allowance,
    Cut,
    DovetailLap,
    DovetailTongue,
    EndRabbet,
    Mitre,
    Pocket,
    Range,
    ShapeCut,
    SlotMortise,
    Taper,
    Tenon,
    Tongue,
    WedgedTenon,
)
from woodwright.part import Board, Side, SideRef
from woodwright.placement import CENTERED, FLUSH, Position, flush_with, mate, offset

__all__ = [
    "Allowance",
    "BlindMitredDovetail",
    "BoxJoint",
    "Bridle",
    "Butt",
    "Button",
    "CrossLap",
    "DadoJoint",
    "DovetailHalfLap",
    "GrooveJoint",
    "HalfBlindDovetail",
    "HalfLap",
    "Housing",
    "Joint",
    "LooseTenon",
    "LooseTongue",
    "MitreCorner",
    "MitreSplice",
    "MitredCornerDovetail",
    "MitredFaceTenon",
    "MitredHalfLap",
    "MitredShoulderTenon",
    "MortiseTenon",
    "RabbetJoint",
    "SlidingDovetail",
    "TeeBridle",
    "ThroughDovetail",
    "TongueAndGroove",
    "TuskTenon",
    "WedgedMortiseTenon",
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

    def pieces(self, placement: bd.Location) -> list[tuple[Board, bd.Location]]:
        """Separate pieces the joint places, e.g. a loose tenon or wedges, with
        their locations in the frame of `parts()[0]`. They must be added to the
        assembly like any other part."""
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
    `across`. With `angle`, part b is turned by that many degrees in the
    plane of side `a` (see `mate`), e.g. a diagonal brace on a face.
    """

    a: SideRef
    b: SideRef
    position: Position = CENTERED
    across: Position = FLUSH
    flush: tuple[SideRef, SideRef] | None = None
    angle: float = 0.0

    def parts(self) -> tuple[Board, Board]:
        return self.a.part, self.b.part

    def placement(self) -> bd.Location:
        flush = self.flush or default_flush(self.a, self.b)
        return mate(
            self.a,
            self.b,
            flush=flush,
            position=self.position,
            across=self.across,
            angle=self.angle,
        )


class Housing(Joint):
    """A side of part b goes into a socket cut into a side of part a.

    Part b reaches beyond its design box into part a (an allowance), either
    with its whole cross-section or with a tenon. The socket is cut where it
    lands, with `clearance` at the bottom if it doesn't go through.
    With `through`, the socket runs out of part a at both ends of the mating
    arris, e.g. a groove along the whole edge. With `stopped`, it stops that
    far short of each of the given sides of part a, e.g. a dado stopped short
    of the front edge so that it doesn't show; where part b would reach into
    the part left standing there, it is notched to clear it (e.g. the front
    corner of a shelf in a stopped dado). Subclasses give the sides, the
    depth and the tenon, and are dataclasses with the fields `position`,
    `across`, `flush` and `clearance` (and `through` and `stopped`, if they
    apply).
    """

    position: Position
    across: Position
    flush: tuple[SideRef, SideRef] | None
    clearance: float
    through: bool = False  # the socket runs the whole length of part a along the arris
    stopped: dict[SideRef, float] | None = None  # the socket stops short of these sides of a

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
        insert = self.sides()[1]
        tenon = self.tenon_cut()
        if tenon is None:
            lo, hi = insert.part.box
            box = [(lo[axis], hi[axis]) for axis in range(3)]
            c, d = insert.coordinate, self.reach()
            box[insert.axis] = (c, c + d) if insert.side.sign > 0 else (c - d, c)
            inserted = [(box[0], box[1], box[2])]
            pockets = [self._pocket(self.socket_box(placement, inserted[0]))]
        else:
            inserted = tenon.boxes()
            pockets = [self._pocket(self.socket_box(placement, box)) for box in tenon.tenon_boxes()]
            for haunch in tenon.haunch_boxes():
                # Without clearance: as deep as the groove the haunch fills.
                haunch_socket = self.socket_box(placement, haunch, clearance=0.0)
                pockets.append(self._pocket(haunch_socket, kind="haunch mortise"))
        notches = self.notches(placement, inserted)
        if tenon is None or not tenon.removes_material:
            return [*pockets, *notches]
        return [*pockets, tenon, *notches]

    def _pocket(self, box: tuple[Range, Range, Range], kind: str | None = None) -> Pocket:
        """The socket, stopped short of those of the sides it would reach."""
        socket = self.sides()[0]
        stopped = {}
        for side, distance in (self.stopped or {}).items():
            if side.part is not socket.part or side.axis == socket.axis:
                raise ValueError(
                    f"a socket in {socket} stops short of a side next to it, not {side}"
                )
            a, b = box[side.axis]
            stop = side.coordinate - side.side.sign * distance
            if (b > stop) if side.side.sign > 0 else (a < stop):
                stopped[side] = distance
        return Pocket(socket, box, kind=kind, stopped=stopped or None)

    def notches(
        self, placement: bd.Location, inserted: list[tuple[Range, Range, Range]]
    ) -> list[Cut]:
        """Notches in part b where it reaches past the stops of the socket, so
        it clears the part of a left standing there; `inserted` are the boxes
        of b (in its frame) going into the socket."""
        insert = self.sides()[1]
        b = insert.part
        lo, hi = b.box
        notches: list[Cut] = []
        for side, distance in (self.stopped or {}).items():
            b_side = _flush_side(b, side, placement)
            stop = [0.0, 0.0, 0.0]
            stop[side.axis] = side.coordinate - side.side.sign * distance
            at = tuple((placement.inverse() * bd.Location(tuple(stop))).position)[b_side.axis]
            for box in inserted:
                ranges = list(box)
                start, end = ranges[b_side.axis]
                ranges[b_side.axis] = (
                    (max(start, at), end) if b_side.side.sign > 0 else (start, min(end, at))
                )
                width = ranges[b_side.axis][1] - ranges[b_side.axis][0]
                if width < _EPS:
                    continue
                # Open where it reaches the sides of b and beyond side `insert`.
                for axis in range(3):
                    a0, a1 = ranges[axis]
                    ranges[axis] = (
                        -INF if a0 <= lo[axis] + _EPS else a0,
                        INF if a1 >= hi[axis] - _EPS else a1,
                    )
                c = insert.coordinate
                ranges[insert.axis] = (c, INF) if insert.side.sign > 0 else (-INF, c)
                removal = Pocket(insert, (ranges[0], ranges[1], ranges[2])).removal()
                text = f"notch {width:g} x {self.reach():g} mm in {insert} at {b_side}"
                notches.append(ShapeCut(b, removal, text))
        return notches

    def socket_box(
        self,
        placement: bd.Location,
        inserted: tuple[Range, Range, Range],
        clearance: float | None = None,
    ) -> tuple[Range, Range, Range]:
        """Ranges of the socket in part a, for a box of part b given in its frame."""
        socket = self.sides()[0]
        clearance = self.clearance if clearance is None else clearance
        box = list(_socket(socket, placement, inserted, clearance))
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
    along a; give `position` e.g. as `offset(100, ref=a.left_end)`. With
    `stopped`, e.g. `{a.front_edge: 15}`, a stopped dado: it stops short of
    the front edge, and the front corner of part b is notched to the stop.
    """

    dado: SideRef
    end: SideRef
    depth: float | None = None
    position: Position = CENTERED
    across: Position = FLUSH
    flush: tuple[SideRef, SideRef] | None = None
    clearance: float = 0.0
    stopped: dict[SideRef, float] | None = None

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
    centered (or as given by `position`). With `lap`, part b gets a rabbet
    too, keeping a lip `lap` thick at its reference face: the two rabbets
    interlock. With `through`, the rabbet runs the whole length of part a,
    e.g. for a box bottom, into the rabbets at the box's corners.
    """

    rabbet: SideRef
    end: SideRef
    at: SideRef
    depth: float | None = None
    lap: float | None = None
    through: bool = False
    position: Position = CENTERED
    across: Position = FLUSH
    flush: tuple[SideRef, SideRef] | None = None
    clearance: float = 0.0
    stopped: dict[SideRef, float] | None = None

    def sides(self) -> tuple[SideRef, SideRef]:
        return self.rabbet, self.end

    def default_flush(self) -> tuple[SideRef, SideRef]:
        return self.at, self.end.part.ref_face

    def with_defaults(self) -> Self:
        return replace(self, depth=self.depth or rules.rabbet_depth(self.rabbet.depth))

    def reach(self) -> float:
        return _require(self.depth)

    def tenon_cut(self) -> Tenon | None:
        if self.lap is None:
            return None
        return Tenon(self.end, length=self.reach(), thickness=self.lap, thickness_offset=0)


@dataclass
class SlidingDovetail(Housing):
    """An end of part b with a dovetail tongue, slid into a dovetail socket across part a.

    Like a dado joint (see `DadoJoint` for the placement), but the socket is
    narrower at the face than at its bottom, so the parts can only slide
    together along it. `thickness` is the tongue's thickness at the shoulder;
    with `half` only one cheek is angled.

    With `end` a face of part b, part b lies flat against part a and its
    whole width goes into a wide, shallow socket, its edges bevelled by
    1:`slope` (`thickness` is then the width at the shoulder, by default
    so that the tongue is as wide as part b at its end): e.g. a batten
    across the underside of a glued-up panel.

    Without `cut_tongue`, the tongue is cut by another sliding dovetail and
    this one only places part b and cuts the socket into part a: e.g. a
    batten whose tongue runs across several boards glued edge to edge, each
    of them housing it.
    """

    socket: SideRef
    end: SideRef
    depth: float | None = None
    thickness: float | None = None
    slope: float = 7.0
    half: bool = False
    cut_tongue: bool = True
    position: Position = CENTERED
    across: Position = FLUSH
    flush: tuple[SideRef, SideRef] | None = None
    clearance: float = 0.0

    def sides(self) -> tuple[SideRef, SideRef]:
        return self.socket, self.end

    def with_defaults(self) -> Self:
        depth = self.depth or rules.dado_depth(self.socket.depth)
        thickness = self.thickness
        if thickness is None and self.end.axis == 2:
            # The whole width at the tongue's end, less the flare at the shoulder.
            thickness = self.end.part.width - (1 if self.half else 2) * depth / self.slope
        return replace(
            self,
            depth=depth,
            thickness=thickness or rules.dovetail_thickness(self.end.part.thickness),
        )

    def reach(self) -> float:
        return _require(self.depth)

    def allowances(self) -> list[Allowance]:
        return super().allowances() if self.cut_tongue else []

    def tongue(self) -> DovetailTongue:
        return DovetailTongue(
            self.end,
            length=self.reach(),
            thickness=_require(self.thickness),
            slope=self.slope,
            half=self.half,
        )

    def cuts(self, placement: bd.Location) -> list[Cut]:
        tongue = self.tongue()
        # The socket is the tongue seen from part a, reaching out of its face.
        socket = placement * tongue.solid(back=self.reach(), beyond=self.clearance)
        description = (
            f"dovetail socket {tongue.thickness:g} mm at the face, {self.reach():g} deep, "
            f"1:{self.slope:g}, in {self.socket}"
        )
        cuts: list[Cut] = [ShapeCut(self.socket.part, socket, description)]
        return [*cuts, tongue] if self.cut_tongue else cuts


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
    stopped: dict[SideRef, float] | None = None

    def sides(self) -> tuple[SideRef, SideRef]:
        return self.groove, self.edge

    def with_defaults(self) -> Self:
        return replace(self, depth=self.depth or rules.groove_depth(self.groove.part.thickness))

    def reach(self) -> float:
        return _require(self.depth)


@dataclass
class TongueAndGroove(Housing):
    """A tongue along an edge (or across an end) of part b in a groove in a side of part a.

    The boards' design widths are their visible faces; the tongue is added.
    It is centered across the thickness unless `tongue_offset` (from the
    reference face) is given: with 0 it is flush with the reference face,
    as on a drawer bottom rabbeted on its underside.

    Without `cut_tongue`, part b goes in whole and only the groove is cut,
    as wide as the tongue would be: e.g. a raised panel whose bevel, planed
    down to the groove's width at its mouth, runs on into it (see `Chamfer`
    with `run_out`).
    """

    tongue: SideRef
    groove: SideRef
    tongue_thickness: float | None = None
    tongue_length: float | None = None
    tongue_offset: float | None = None
    cut_tongue: bool = True
    through: bool = True  # the groove runs the whole length of part a
    position: Position = CENTERED
    across: Position = FLUSH
    flush: tuple[SideRef, SideRef] | None = None
    clearance: float = 0.0
    stopped: dict[SideRef, float] | None = None

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
        return Tongue(
            self.tongue,
            length=self.reach(),
            thickness=_require(self.tongue_thickness),
            thickness_offset=self.tongue_offset,
        )

    def cuts(self, placement: bd.Location) -> list[Cut]:
        cuts = super().cuts(placement)
        return cuts if self.cut_tongue else [c for c in cuts if not isinstance(c, Tongue)]


@dataclass
class MortiseTenon(Housing):
    """A tenon on an end of one part, in a mortise in a side of the other.

    The reference faces of both parts are flush (see `across` to change
    that). The tenon has a `shoulder` on both edges, or a pair of them (at
    the front edge, at the back edge), and is centered across the
    thickness unless `tenon_offset` (from the reference face) is given.
    The mortise is cut where the tenon goes, with some clearance at its
    bottom; a tenon as long as the mortised part is deep goes through.

    With `haunch`, an edge of the tenoned part (e.g. the outer edge of a
    rail), the tenon gets a haunch towards it, `haunch_length` long (by
    default as deep as a panel groove), and the mortised part a haunch
    mortise. It fills a groove running out of the mortised part, or the
    shoulder of a wide rail (e.g. a table apron) set down from the end of
    the mortised part, so its mortise doesn't run out of it.

    With `mitre`, a face of the tenoned part, the end of the tenon is mitred
    at 45 degrees, shorter at the cheek towards that face: for two tenons
    meeting inside a leg. The mortise stays rectangular.

    With `tenon_chamfer`, the arrises around the end of the tenon are
    chamfered, e.g. on a through tenon a bit longer than the mortised part
    is deep, so that it stands proud of it.

    With `tenons`, there are that many tenons side by side between the
    shoulders, e.g. twin tenons on a wide rail, `tenon_gap` apart (by
    default as wide as the tenons), each in its own mortise. The other
    options apply to each of them (the haunch to the outer one).

    With `thickness_tenons`, there are that many tenons one beside the
    other across the thickness, e.g. on a thick, square rail,
    `thickness_gap` apart (by default as thick as the tenons). Each is
    `tenon_thickness` thick, by default about as thick as the gaps and the
    cheek shoulders; `tenon_offset` is then to the nearest of them. With
    `tenons` too, they make a grid, each in its own mortise. A haunch is
    beside each of them across the thickness; a mitre runs across all.
    """

    tenon: SideRef
    mortise: SideRef
    position: Position = CENTERED
    tenon_thickness: float | None = None
    tenon_length: float | None = None
    shoulder: float | tuple[float, float] = 5.0  # on both edges of the tenoned part
    clearance: float = 2.0  # extra mortise depth
    tenon_offset: float | None = None
    haunch: SideRef | None = None
    haunch_length: float | None = None
    mitre: SideRef | None = None
    tenon_chamfer: float = 0.0
    tenons: int = 1
    tenon_gap: float | None = None
    thickness_tenons: int = 1
    thickness_gap: float | None = None
    across: Position = FLUSH
    flush: tuple[SideRef, SideRef] | None = None

    def sides(self) -> tuple[SideRef, SideRef]:
        return self.mortise, self.tenon

    def with_defaults(self) -> Self:
        haunch_length = self.haunch_length
        if self.haunch is not None and haunch_length is None:
            haunch_length = rules.groove_depth(self.mortise.part.thickness)
        gap = self.tenon_gap
        if self.tenons > 1 and gap is None:
            gap = self._shoulders_apart() / (2 * self.tenons - 1)
        thickness = self.tenon_thickness or rules.tenon_thickness(
            self.tenon.part.thickness, count=self.thickness_tenons
        )
        thickness_gap = self.thickness_gap
        if self.thickness_tenons > 1 and thickness_gap is None:
            thickness_gap = thickness
        return replace(
            self,
            tenon_thickness=thickness,
            tenon_length=self.tenon_length or rules.tenon_length(self.mortise.depth),
            haunch_length=haunch_length,
            tenon_gap=gap,
            thickness_gap=thickness_gap,
        )

    def reach(self) -> float:
        return _require(self.tenon_length)

    def _shoulders(self) -> tuple[float, float]:
        """At the front edge and at the back edge (along the side)."""
        shoulder = _require(self.shoulder)
        return (shoulder, shoulder) if isinstance(shoulder, int | float) else shoulder

    def _shoulders_apart(self) -> float:
        """The width of the tenon, or of all the tenons together."""
        front, back = self._shoulders()
        return self.tenon.size[0] - front - back

    def tenon_cut(self) -> Tenon:
        return Tenon(
            self.tenon,
            length=self.reach(),
            thickness=_require(self.tenon_thickness),
            width=self._shoulders_apart(),
            width_offset=self._shoulders()[0],
            thickness_offset=self.tenon_offset,
            haunch=self.haunch,
            haunch_length=self.haunch_length,
            mitre=self.mitre,
            chamfer=self.tenon_chamfer,
            count=self.tenons,
            gap=self.tenon_gap or 0.0,
            thickness_count=self.thickness_tenons,
            thickness_gap=self.thickness_gap or 0.0,
        )


@dataclass
class WedgedMortiseTenon(MortiseTenon):
    """A through mortise and tenon, the tenon spread by wedges driven into saw
    kerfs in its end, into a mortise flared towards the outside.

    The `wedges` are separate parts, one per kerf: one or two per tenon (see
    `tenons` and `thickness_tenons`), in the order of the kerfs along the
    tenon, the top tenons' first. They are given as
    made: as thick as the tenon (which by default they set), as long as the
    kerfs are deep, and as wide at their heads as the `kerf` plus the
    spread of the tenon (twice the spread for one kerf in the middle). The
    joint tapers them to fit. Two kerfs lie `kerf_inset` in from the edges of
    the tenon (by default a fifth of its width), so the outer parts of the
    tenon bend out into the flare at each end of the mortise; one kerf
    spreads both halves of the tenon. The mortise is flared over the depth
    of the kerfs (less what the tenon stands proud) and straight below.

    The tenon goes through, by default flush with the far side of the
    mortised part; it may stand proud of it, then the wedges are as long. The
    model is of the joint glued up, the tenon spread (see `WedgedTenon`).
    """

    wedges: tuple[Board, ...] = ()
    kerf: float = 2.0
    kerf_inset: float | None = None

    def __post_init__(self) -> None:
        if not self.wedges:
            raise ValueError("a wedged tenon needs wedges")
        first = self.wedges[0]
        size = (first.length, first.width, first.thickness)
        if any((w.length, w.width, w.thickness) != size for w in self.wedges):
            raise ValueError("the wedges must be of the same size")
        if len(self.wedges) not in (self._count(), 2 * self._count()):
            raise ValueError("a wedged tenon has one or two wedges per tenon")
        if self.mitre is not None or self.tenon_chamfer:
            raise ValueError("a wedged tenon has a square end")

    def with_defaults(self) -> Self:
        joint = replace(
            self,
            tenon_thickness=self.tenon_thickness or self.wedges[0].thickness,
            tenon_length=self.tenon_length or self.mortise.depth,
        )
        joint = super(WedgedMortiseTenon, joint).with_defaults()
        if joint.reach() < self.mortise.depth - _EPS:
            raise ValueError("a wedged tenon goes through the mortised part")
        if abs(_require(joint.tenon_thickness) - self.wedges[0].thickness) > _EPS:
            raise ValueError("the wedges must be as thick as the tenon")
        return joint

    @property
    def kerfs(self) -> int:
        """Per tenon."""
        return len(self.wedges) // self._count()

    def _count(self) -> int:
        """Of all the tenons."""
        return self.tenons * self.thickness_tenons

    def tenon_cut(self) -> WedgedTenon:
        tenon = super().tenon_cut()
        wedge = self.wedges[0]
        return WedgedTenon(
            **{field.name: getattr(tenon, field.name) for field in fields(tenon)},
            kerfs=self.kerfs,
            kerf=self.kerf,
            kerf_inset=self.kerf_inset,
            kerf_depth=wedge.length,
            flare=(wedge.width - self.kerf) / (3 - self.kerfs),
            proud=self.reach() - self.mortise.depth,
        )

    def pieces(self, placement: bd.Location) -> list[tuple[Board, bd.Location]]:
        locations = self.tenon_cut().wedge_locations()
        return [(w, placement * loc) for w, loc in zip(self.wedges, locations, strict=True)]

    def cuts(self, placement: bd.Location) -> list[Cut]:
        tenon = self.tenon_cut()
        mortises = "mortises" if self._count() > 1 else "mortise"
        flare = ShapeCut(
            self.mortise.part,
            placement * tenon.flare_solid(),
            f"{mortises} flared {tenon.flare:g} mm at the ends over "
            f"{tenon.kerf_depth - tenon.proud:g}, in {self.mortise}",
        )
        tapers: list[Cut] = []
        length = None if tenon.proud < _EPS else tenon.kerf_depth - tenon.proud
        for wedge in self.wedges:
            edges = [wedge.back_edge] if self.kerfs == 2 else [wedge.front_edge, wedge.back_edge]
            tapers += [
                Taper(edge, end=wedge.right_end, amount=tenon.flare, length=length)
                for edge in edges
            ]
        return [*super().cuts(placement), flare, *tapers]


@dataclass
class TuskTenon(MortiseTenon):
    """A tusk tenon: a long through tenon held by a wedge (a tusk, a key)
    through a mortise in its end, a knock-down joint, e.g. for the stretchers
    of a workbench or a trestle table.

    The tenon goes through the mortised part (the leg) and stands
    `protrusion` proud of its outer side (by default two and a half times
    the wedge's width). The `wedge` is a separate part, given as made: a
    straight blank as long, wide (at its head) and thick as the wedge; the
    joint tapers its back edge by 1:`wedge_slope` towards its right end, the
    tip. It goes through a mortise in the protruding part of the tenon, its
    straight front edge bearing on the outer side of the leg, its tapered
    edge on the outer end of the mortise, which is sloped to match. The
    mortise starts `draw` inside the outer side of the leg, so the wedge
    bears on the leg, not on the inner end of the mortise: driven in, it
    pulls the tenon out of the leg and the shoulders tight against it. The
    wedge is centered on the tenon both ways, so its head and its tip stick
    out on either side. The model is of the joint assembled, the wedge
    driven home.

    `wedge_head` is the side of the mortised part the head of the wedge
    points to (by default its right end). With an end, the wedge is
    parallel to the stile (the leg's length): with the usual placement it
    goes through the tenon's width, from one edge to the other, e.g. upright
    through the tenon of a horizontal stretcher in a standing leg, and is as
    thick as a third or so of the tenon. With a face (or an edge), the wedge
    is perpendicular to the stile: it goes through the tenon's thickness,
    from one cheek to the other, e.g. lying level through an upright tenon,
    and may be thicker, its thickness across the tenon's width.
    """

    wedge: Board | None = None
    wedge_head: SideRef | None = None
    wedge_slope: float = 8.0
    protrusion: float | None = None
    draw: float = 3.0

    def __post_init__(self) -> None:
        if self.wedge is None:
            raise ValueError("a tusk tenon needs a wedge")
        if self.tenons != 1 or self.thickness_tenons != 1:
            raise ValueError("a tusk tenon is a single tenon")
        if self.mitre is not None:
            raise ValueError("a tusk tenon has a square end")
        if self.wedge_head is not None and (
            self.wedge_head.part is not self.mortise.part
            or self.wedge_head.axis == self.mortise.axis
        ):
            raise ValueError(f"the wedge's head points to a side next to {self.mortise}")

    def with_defaults(self) -> Self:
        if self.tenon_length is not None:
            raise ValueError("a tusk tenon is as long as given by its protrusion")
        wedge = self._wedge()
        protrusion = 2.5 * wedge.width if self.protrusion is None else self.protrusion
        joint = replace(
            self,
            protrusion=protrusion,
            tenon_length=self.mortise.depth + protrusion,
            wedge_head=self.wedge_head or self.mortise.part.right_end,
        )
        return super(TuskTenon, joint).with_defaults()

    def _wedge(self) -> Board:
        assert self.wedge is not None
        return self.wedge

    def taper(self) -> float:
        """How much narrower the wedge is at its tip than at its head."""
        return self._wedge().length / self.wedge_slope

    def _wedge_frame(self, placement: bd.Location) -> tuple[bd.Location, int, int]:
        """The location of the wedge in the frame of the tenoned part, the axis
        of that frame it runs along and the one its thickness runs along."""
        wedge, tenon = self._wedge(), self.tenon
        head = _direction(placement.inverse(), _require(self.wedge_head).normal)
        along = _axis(head)
        across = 3 - tenon.axis - along
        box = self.tenon_cut().tenon_box()
        # At the outer side of the mortised part, in the middle of the tenon.
        center = [0.0, 0.0, 0.0]
        center[tenon.axis] = tenon.coordinate + tenon.side.sign * self.mortise.depth
        for axis in (along, across):
            center[axis] = sum(box[axis]) / 2
        x_dir = -head  # from the head to the tip
        z_dir = x_dir.cross(tenon.normal)  # the wedge's back edge faces outwards
        origin = bd.Vector(*center) + head * (wedge.length / 2) + z_dir * (wedge.thickness / 2)
        return bd.Location(bd.Plane(origin, x_dir=x_dir, z_dir=z_dir)), along, across

    def pieces(self, placement: bd.Location) -> list[tuple[Board, bd.Location]]:
        return [(self._wedge(), placement * self._wedge_frame(placement)[0])]

    def cuts(self, placement: bd.Location) -> list[Cut]:
        wedge, tenon = self._wedge(), self.tenon
        location, along, across = self._wedge_frame(placement)
        box = self.tenon_cut().tenon_box()
        lo, hi = box[along]
        if wedge.length < hi - lo + _EPS:
            raise ValueError("the wedge must be longer than the tenon it goes through")
        if wedge.thickness > box[across][1] - box[across][0] - _EPS:
            raise ValueError("the wedge must be thinner than the tenon it goes through")
        # The mortise in the wedge's frame: from `draw` inside its front edge
        # to its tapered back edge, as thick as the wedge.
        k, w, length = self.taper() / wedge.length, wedge.width, wedge.length
        points = [(0, -self.draw), (length, -self.draw), (length, w - length * k), (0, w)]
        mortise = location * (
            bd.Pos(0, 0, -wedge.thickness) * bd.extrude(bd.Polygon(*points), amount=wedge.thickness)
        )
        # Where the mortise meets the edges of the tenon, from the head.
        widths = [w - k * (length - (hi - lo)) / 2, w - k * (length + (hi - lo)) / 2]
        if widths[0] > _require(self.protrusion) - _EPS:
            raise ValueError("the wedge's mortise runs out of the end of the tenon")
        opposite = next(s for s in Side if s.axis == self.mortise.axis and s != self.mortise.side)
        outer = SideRef(self.mortise.part, opposite)
        sizes = " to ".join(f"{round(self.draw + width, 1):g}" for width in widths)
        description = (
            f"wedge mortise {wedge.thickness:g} x {sizes} mm through the tenon on {tenon}, "
            f"its outer end sloped 1:{self.wedge_slope:g}, from {self.draw:g} inside {outer}"
        )
        taper = Taper(wedge.back_edge, end=wedge.right_end, amount=self.taper())
        return [*super().cuts(placement), ShapeCut(tenon.part, mortise, description), taper]


@dataclass
class MitredShoulderTenon(MortiseTenon):
    """A mortise and tenon whose shoulders are partly mitred, e.g. in a frame
    of square-ish stock.

    The tenoned part reaches `mitre_depth` into the mortised part (by default
    a third of its width) with its whole cross-section, into a notch, and
    the tenon starts there. At each of `mitred`, edges of the tenoned part
    (by default both of them, for a T-joint), the notch is mitred at 45
    degrees back to the side of the mortised part: the parts meet on a short
    mitre there and along the mortised part in between. For an L-shaped
    corner, mitre only the inner edge; the tenon may then go through, as long
    as the material behind the notch. The design length of the tenoned part
    is to the side of the mortised part, as for a plain tenon.

    The tenon may reach under the mitres, which makes it wider and the joint
    sturdier: its shoulders are by default half as deep as the mitres at the
    mitred edges, as deep as them at the others (e.g. to keep material at
    the end of the stile at a corner). Under a mitre the tenon starts at the
    side of the mortised part, elsewhere at the bottom of the notch; its
    length is measured from there. The mortise is cut from the side of the
    mortised part, through the notch and the mitres.
    """

    shoulder: float | tuple[float, float] | None = None  # by default from the mitre depth
    mitre_depth: float | None = None
    mitred: tuple[SideRef, ...] | None = None

    def with_defaults(self) -> Self:
        board = self.tenon.part
        depth = self.mitre_depth
        if depth is None:
            depth = self.mortise.depth / 3
        mitred = self.mitred
        if mitred is None:
            mitred = (board.front_edge, board.back_edge) if self.tenon.axis == 0 else ()
        shoulder = self.shoulder
        if shoulder is None:
            front, back = (
                depth / 2 if edge in mitred else depth
                for edge in (board.front_edge, board.back_edge)
            )
            shoulder = (front, back)
        tenon_length = self.tenon_length or rules.tenon_length(self.mortise.depth - depth)
        joint = replace(
            self,
            mitre_depth=depth,
            mitred=mitred,
            shoulder=shoulder,
            tenon_length=tenon_length,
        )
        return super(MitredShoulderTenon, joint).with_defaults()

    def allowances(self) -> list[Allowance]:
        return self.tenon_cut().allowances()

    def tenon_cut(self) -> Tenon:
        depth, mitred = _require(self.mitre_depth), _require(self.mitred)
        tenon = replace(super().tenon_cut(), mitre_depth=depth, mitred=mitred)
        lo, hi = tenon.tenon_box()[1 - self.tenon.axis]
        part_lo, part_hi = self.tenon.part.box
        for edge in mitred:
            shoulder = lo - part_lo[edge.axis] if edge.side.sign < 0 else part_hi[edge.axis] - hi
            if shoulder < _EPS:
                raise ValueError(f"the tenon must not run out of the mitre at {edge}")
        return tenon

    def cuts(self, placement: bd.Location) -> list[Cut]:
        cuts = super().cuts(placement)
        tenon = self.tenon_cut()
        # The mortises are open to the notch, so cut them from the side.
        for i in range(len(tenon.tenon_boxes())):
            mortise = cuts[i]
            assert isinstance(mortise, Pocket)
            box = list(mortise.box)
            axis, (a, b) = self.mortise.axis, box[self.mortise.axis]
            box[axis] = (a, INF) if self.mortise.side.sign > 0 else (-INF, b)
            cuts[i] = replace(mortise, box=(box[0], box[1], box[2]))
        mitred = _require(self.mitred)
        ends = {0: "", 1: ", mitred at one end", 2: ", mitred at both ends"}[len(mitred)]
        width = self.tenon.size[0]
        description = f"notch {width:g} long, {tenon.mitre_depth:g} deep{ends}, in {self.mortise}"
        notch = placement * tenon.reach_solid()
        return [*cuts, ShapeCut(self.mortise.part, notch, description)]


@dataclass
class LooseTenon(Joint):
    """Two parts joined by a loose (floating) tenon glued into a mortise in each.

    Side `b` of part b (an end, or an edge) butts against side `a` of part a,
    placed as by `Butt`. The loose tenon `tenon` is a separate part, e.g. a
    strip planed as thick as the mortises are wide: it crosses the joint
    line along its length (and grain), reaching `depth` into part a (by
    default half its length) and the rest into part b. Its reference face
    faces the same way as b's; on side `b` it is centered, or placed by
    `tenon_position` (along the arris with b's reference face) and
    `tenon_offset` (below b's reference face). Each mortise is `clearance`
    deeper than the tenon reaches, unless it goes through.
    """

    a: SideRef
    b: SideRef
    tenon: Board
    depth: float | None = None
    tenon_position: Position = CENTERED
    tenon_offset: float | None = None
    position: Position = CENTERED
    across: Position = FLUSH
    flush: tuple[SideRef, SideRef] | None = None
    clearance: float = 2.0

    def __post_init__(self) -> None:
        if self.b.axis == 2:
            raise ValueError(f"a loose tenon goes into an end or an edge, not into {self.b}")

    def parts(self) -> tuple[Board, Board]:
        return self.a.part, self.b.part

    def with_defaults(self) -> Self:
        depth = self.tenon.length / 2 if self.depth is None else self.depth
        if not 0 < depth < self.tenon.length:
            raise ValueError("a loose tenon must reach into both parts")
        return replace(self, depth=depth)

    def placement(self) -> bd.Location:
        flush = self.flush or default_flush(self.a, self.b)
        return mate(self.a, self.b, flush=flush, position=self.position, across=self.across)

    def tenon_location(self) -> bd.Location:
        """Of the loose tenon in the frame of part b, its left end inside b."""
        b = self.b.part
        across = CENTERED if self.tenon_offset is None else offset(self.tenon_offset)
        return mate(
            self.b,
            self.tenon.left_end,
            flush=(b.ref_face, self.tenon.ref_face),
            position=self.tenon_position,
            across=across,
            gap=-(self.tenon.length - _require(self.depth)),
        )

    def pieces(self, placement: bd.Location) -> list[tuple[Board, bd.Location]]:
        return [(self.tenon, placement * self.tenon_location())]

    def cuts(self, placement: bd.Location) -> list[Cut]:
        lo, hi = self.tenon.box
        box = (lo[0], hi[0]), (lo[1], hi[1]), (lo[2], hi[2])
        in_b = self.tenon_location()
        return [
            Pocket(side, _socket(side, loc, box, self.clearance))
            for side, loc in [(self.a, placement * in_b), (self.b, in_b)]
        ]


@dataclass
class LooseTongue(Joint):
    """Two parts edge to edge, joined by a loose tongue (a spline) glued into a
    groove in each.

    Side `b` of part b (an edge, or an end) butts against side `a` of part
    a, placed as by `Butt`. The loose tongue `tongue` is a separate part, a
    strip planed as thick as the grooves are wide, its length along the
    joint and so its grain too: simple to make, if weaker across the joint
    than a strip of plywood or of short grain. Its width crosses the joint
    line, reaching `depth` into part a (by default half its width) and the
    rest into part b. Its reference face faces the same way as b's; along
    side `b` it is centered, or placed by `tongue_position` (along the
    arris with b's reference face), across it by `tongue_offset` (below b's
    reference face). Each groove is `clearance` deeper than the tongue
    reaches, for the glue.

    With `through` (the default), the grooves run the whole length of the
    parts along the joint, as cut on a table saw, showing at their ends.
    Without, they are stopped grooves as long as the tongue, as cut with a
    router, e.g. hidden by a tongue shorter than the boards.
    """

    a: SideRef
    b: SideRef
    tongue: Board
    depth: float | None = None
    through: bool = True
    tongue_position: Position = CENTERED
    tongue_offset: float | None = None
    position: Position = CENTERED
    across: Position = FLUSH
    flush: tuple[SideRef, SideRef] | None = None
    clearance: float = 1.0

    def __post_init__(self) -> None:
        if self.b.axis == 2:
            raise ValueError(f"a loose tongue goes into an edge or an end, not into {self.b}")

    def parts(self) -> tuple[Board, Board]:
        return self.a.part, self.b.part

    def with_defaults(self) -> Self:
        depth = self.tongue.width / 2 if self.depth is None else self.depth
        if not 0 < depth < self.tongue.width:
            raise ValueError("a loose tongue must reach into both parts")
        return replace(self, depth=depth)

    def placement(self) -> bd.Location:
        flush = self.flush or default_flush(self.a, self.b)
        return mate(self.a, self.b, flush=flush, position=self.position, across=self.across)

    def tongue_location(self) -> bd.Location:
        """Of the loose tongue in the frame of part b, its front edge inside b."""
        b = self.b.part
        across = CENTERED if self.tongue_offset is None else offset(self.tongue_offset)
        return mate(
            self.b,
            self.tongue.front_edge,
            flush=(b.ref_face, self.tongue.ref_face),
            position=self.tongue_position,
            across=across,
            gap=-(self.tongue.width - _require(self.depth)),
        )

    def pieces(self, placement: bd.Location) -> list[tuple[Board, bd.Location]]:
        return [(self.tongue, placement * self.tongue_location())]

    def cuts(self, placement: bd.Location) -> list[Cut]:
        lo, hi = self.tongue.box
        box = (lo[0], hi[0]), (lo[1], hi[1]), (lo[2], hi[2])
        in_b = self.tongue_location()
        grooves: list[Cut] = []
        for side, loc in [(self.a, placement * in_b), (self.b, in_b)]:
            ranges = list(_socket(side, loc, box, self.clearance))
            along = _axis(_direction(loc, bd.Vector(1, 0, 0)))  # the tongue's length
            # Stopped where the tongue ends (unless it runs out of the part).
            start, end = ranges[along]
            stopped = {}
            if not self.through:
                part = side.part
                for stop in map(part.side, Side):
                    if stop.axis == along:
                        bound = end if stop.side.sign > 0 else start
                        if abs(bound) != INF:
                            stopped[stop] = abs(stop.coordinate - bound)
            ranges[along] = (-INF, INF)
            box_ranges = (ranges[0], ranges[1], ranges[2])
            grooves.append(Pocket(side, box_ranges, stopped=stopped or None))
        return grooves


@dataclass
class Bridle(Housing):
    """A tenon over the whole width of an end of part b, through a slot in part a.

    For an L-shaped corner the slot is at an end of part a, e.g. with
    `position=flush_with(a.left_end)`; it then is a slot mortise. For a
    T-shaped bridle, with the slot in part b, see `TeeBridle`. The tenon
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
class TeeBridle(Joint):
    """A T-shaped bridle joint: a slot in the end of part b straddles part a,
    which is cut down to a tongue by a dado across each of its faces.

    Part b comes to part a at its side `edge` and reaches across it, its
    end flush with a's opposite side: its design length is overall. The
    slot is `slot_thickness` wide (by default a third of part a, as is
    usual for bridles), centered across b's thickness unless `slot_offset`
    (from b's reference face) is given. The reference faces are flush (see
    `across` to change that); along part a, b is centered (or as given by
    `position`).
    """

    slot: SideRef
    edge: SideRef
    position: Position = CENTERED
    slot_thickness: float | None = None
    slot_offset: float | None = None
    across: Position = FLUSH
    flush: tuple[SideRef, SideRef] | None = None

    def __post_init__(self) -> None:
        if self.slot.axis != 0:
            raise ValueError(f"a bridle's slot is in an end, not in {self.slot}")
        if self.edge.axis != 1:
            raise ValueError(f"a T-bridle straddles an edge, not {self.edge}")

    def parts(self) -> tuple[Board, Board]:
        return self.edge.part, self.slot.part

    def with_defaults(self) -> Self:
        thickness = self.slot_thickness or rules.tenon_thickness(self.edge.part.thickness)
        return replace(self, slot_thickness=thickness)

    def slot_cut(self) -> SlotMortise:
        return SlotMortise(
            self.slot,
            width=_require(self.slot_thickness),
            depth=self.edge.depth,
            distance=self.slot_offset,
        )

    def placement(self) -> bd.Location:
        flush = self.flush or default_flush(self.edge, self.slot)
        return mate(
            self.edge,
            self.slot,
            flush=flush,
            position=self.position,
            across=self.across,
            gap=-self.edge.depth,
        )

    def cuts(self, placement: bd.Location) -> list[Cut]:
        slot = self.slot_cut()
        a, b = self.parts()
        # The cheeks either side of the slot, in b's frame, give the dados in a.
        (x0, x1), _, (z0, z1) = slot.ranges()
        x = (max(x0, b.box[0][0]), min(x1, b.box[1][0]))
        y = (b.box[0][1], b.box[1][1])
        dados = []
        for z in [(z1, b.box[1][2]), (b.box[0][2], z0)]:
            if z[1] - z[0] < _EPS:
                continue
            box = _socket(a.top_face, placement, (x, y, z), 0.0)
            face = a.top_face if box[2][1] == INF else a.bottom_face
            dados.append(Pocket(face, box))
        return [slot, *dados]


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
class DovetailHalfLap(HalfLap):
    """A half lap whose lap is dovetailed across the face, in a dovetail-shaped
    socket, so that part b can't be pulled out of part a along its length.

    Placed and cut to half thickness as `HalfLap`. The lap is a tail as wide
    as part b at its end, its edges sloping in by 1:`slope` to the shoulder,
    where part b is cut back beside it; part a gets a socket of the tail's
    shape. `sloped` are the edges of part b that slope: by default both,
    except one flush with an end of part a, i.e. at an L-shaped corner it is
    a half dovetail sloped at the inner edge.
    """

    slope: float = 7.0
    sloped: tuple[SideRef, ...] | None = None

    def with_defaults(self) -> Self:
        joint = super().with_defaults()
        if joint.sloped is None:
            loc, a = joint.placement(), joint.socket.part
            b = joint.lap.part
            ends = [a.left_end, a.right_end]

            def at_end(edge: SideRef) -> bool:
                normal = _direction(loc, edge.normal)
                point = (loc * bd.Location(edge.plane.origin)).position
                return any(
                    (normal - end.normal).length < _EPS and abs(point.X - end.coordinate) < _EPS
                    for end in ends
                )

            sloped = tuple(edge for edge in (b.front_edge, b.back_edge) if not at_end(edge))
            joint = replace(joint, sloped=sloped)
        return joint

    def tenon_cut(self) -> DovetailLap:
        lap = super().tenon_cut()
        return DovetailLap(
            **{field.name: getattr(lap, field.name) for field in fields(lap)},
            slope=self.slope,
            sloped=self.sloped,
        )

    def cuts(self, placement: bd.Location) -> list[Cut]:
        lap = self.tenon_cut()
        a = self.socket.part
        box = self.socket_box(placement, lap.tenon_box())
        socket = Pocket(self.socket, box).removal() & (placement * lap.tail())
        # The face of part a the socket is cut from: the one part b's lap is flush with.
        b = self.lap.part
        lap_face = b.top_face if self.over else b.bottom_face
        normal = _direction(placement, lap_face.normal)
        face = next(s for s in map(a.side, Side) if (s.normal - normal).length < _EPS)
        lo, hi = a.box
        start, stop = box[face.axis]
        depth = min(stop, hi[face.axis]) - max(start, lo[face.axis])
        description = (
            f"dovetail socket {round(lap.shoulder_width, 1):g} to {b.width:g} mm, {depth:g} deep, "
            f"1:{self.slope:g}, in {face}"
        )
        return [ShapeCut(a, socket, description), lap]


class _CornerJoint(Joint):
    """Two ends interlocking at a corner, each board reaching through the other.

    The end of part a (`ends()[0]`) gets pins or fingers, the end of part b
    the tails or fingers between them. Both boards reach through each other,
    so each gets an allowance of the other's thickness. Part a's reference
    face is outside; `flush` are the sides kept flush along the corner (by
    default the reference edges). Part a may be narrower than part b, e.g.
    the back of a drawer sitting on its bottom. The geometry is built once
    in the frame of part a and split: subclasses give the outlines of part
    a's pins (or fingers) across the corner.
    """

    flush: tuple[SideRef, SideRef] | None

    def ends(self) -> tuple[SideRef, SideRef]:
        raise NotImplementedError

    def parts(self) -> tuple[Board, Board]:
        a, b = self.ends()
        return a.part, b.part

    def __post_init__(self) -> None:
        a, b = self.ends()
        if a.axis != 0 or b.axis != 0:
            raise ValueError(f"{type(self).__name__} is cut on the ends of boards")
        if a.part.width > b.part.width:
            raise ValueError(f"{a.part.name} must not be wider than {b.part.name}")

    def reach(self) -> float:
        """How far part b reaches into part a, from its inside face."""
        return self.ends()[0].part.thickness

    def allowances(self) -> list[Allowance]:
        # Part b reaches into part a, part a past part b.
        a, b = self.ends()
        return [Allowance(b, self.reach()), Allowance(a, b.part.thickness)]

    def placement(self) -> bd.Location:
        # Part b's end lies against the inside face of part a, its outside
        # face level with the end of part a's blank.
        (a_end, b_end), (a, b) = self.ends(), self.parts()
        return mate(
            a.bottom_face,
            b_end,
            flush=self.flush or (a.ref_edge, b.ref_edge),
            position=offset(-b.thickness, ref=a_end),
        )

    def cuts(self, placement: bd.Location) -> list[Cut]:
        a, b = self.parts()
        corner = self._corner()
        sockets, dovetails = self._descriptions()
        return [
            ShapeCut(a, self._block() - corner, sockets),
            ShapeCut(b, placement.inverse() * corner, dovetails),
        ]

    def _x_range(self, length: float) -> Range:
        """Along part a, from the inside face of part b outwards by `length`."""
        a_end = self.ends()[0]
        c = a_end.coordinate
        return (c, c + length) if a_end.side.sign > 0 else (c - length, c)

    def _block(self) -> bd.Part:
        """Where part b meets part a, beyond part a's end, in its frame."""
        a, b = self.parts()
        x0, _ = self._x_range(b.thickness)
        return bd.Pos(x0, 0, -a.thickness) * bd.Box(
            b.thickness, a.width, self.reach(), align=(bd.Align.MIN,) * 3
        )

    def _corner(self) -> bd.Part:
        """Part a's share of the block: its pins (or fingers)."""
        return self._pins(self.ends()[1].part.thickness)

    def _pins(self, length: float) -> bd.Part:
        """The pins, `length` long along part a from the inside face of part b.

        Their profiles are drawn across the width (x) and the thickness (y) of
        part a and extruded along its length.
        """
        x0, _ = self._x_range(length)
        profile_plane = bd.Plane((x0, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
        solids = [
            bd.extrude(profile_plane * bd.Polygon(*points), amount=length)
            for points in self._pin_profiles()
        ]
        return functools.reduce(operator.add, solids)

    def _pin_profiles(self) -> list[list[tuple[float, float]]]:
        """Outlines of part a's pins as (across the width, along the normal)."""
        raise NotImplementedError

    def _descriptions(self) -> tuple[str, str]:
        """Of the cuts on part a and on part b."""
        raise NotImplementedError


@dataclass
class BoxJoint(_CornerJoint):
    """A box (finger) joint: both ends cut into square fingers that interlock.

    The fingers alternate across the width, part a's at its reference edge;
    each finger is as long as the other board is thick, so the boards reach
    through each other, as with through dovetails: part a's reference face
    is outside, `flush` are the sides kept flush (by default the reference
    edges). The fingers are all equally wide: `fingers` of them in all, or
    else the odd number of them coming closest to `finger_width` (by default
    the thickness of part a), so that part a has fingers at both edges and
    the width is used up without a narrow finger left over.
    """

    a: SideRef
    b: SideRef
    fingers: int | None = None
    finger_width: float | None = None
    flush: tuple[SideRef, SideRef] | None = None

    def ends(self) -> tuple[SideRef, SideRef]:
        return self.a, self.b

    def with_defaults(self) -> Self:
        width = self.a.part.width
        fingers = self.fingers
        if fingers is None:
            nominal = self.finger_width or rules.finger_width(self.a.part.thickness)
            fingers = max(1, 2 * round((width / nominal - 1) / 2) + 1)
        if fingers < 2:
            raise ValueError("a box joint needs at least two fingers")
        return replace(self, fingers=fingers, finger_width=width / fingers)

    def _pin_profiles(self) -> list[list[tuple[float, float]]]:
        # Part a's fingers: every other one, from its reference edge (y = 0).
        t, w = self.a.part.thickness, _require(self.finger_width)
        return [
            [(u, 0), (u, -t), (u + w, -t), (u + w, 0)]
            for u in (i * w for i in range(0, _require(self.fingers), 2))
        ]

    def _descriptions(self) -> tuple[str, str]:
        n, w = _require(self.fingers), round(_require(self.finger_width), 1)
        a, b = self.parts()
        return (
            f"box joint, {(n + 1) // 2} fingers {w:g} mm wide, {b.thickness:g} long",
            f"box joint, {n // 2} fingers {w:g} mm wide, {a.thickness:g} long",
        )


@dataclass
class ThroughDovetail(_CornerJoint):
    """Through dovetails at a corner of two boards.

    The tails are cut on an end of one board, the pins on an end of the
    other (any ends, so a board may have pins or tails at both ends). Both
    boards reach through each other, so each gets an allowance of the
    other's thickness. The pin board's reference face is outside; `flush`
    are the sides kept flush along the corner (by default the reference
    edges). The pin board may be narrower than the tail board, e.g. the back
    of a drawer sitting on its bottom; the tails are laid out across it. The
    geometry is built once in the frame of the pin board and split.
    """

    tails: SideRef
    pins: SideRef
    tail_count: int = 4
    slope: float = 7.0  # 1:slope, between 1:6 (softwood) and 1:8 (hardwood)
    pin_width: float = 8.0  # narrowest, at the end of the tails
    half_pin_width: float = 10.0
    flush: tuple[SideRef, SideRef] | None = None

    def ends(self) -> tuple[SideRef, SideRef]:
        return self.pins, self.tails

    def _descriptions(self) -> tuple[str, str]:
        n = self.tail_count
        return f"sockets for {n} dovetails", f"{n} dovetails, slope 1:{self.slope:g}"

    def _tail_length(self) -> float:
        """How long the tails are: as far as the tail board reaches into the pin board."""
        return self.reach()

    def _span(self) -> Range:
        """Where the dovetails are laid out across the width of the pin board."""
        return 0.0, self.pins.part.width

    def _pin_length(self) -> float:
        """How far the pins reach along the pin board: through the tail board."""
        return self.tails.part.thickness

    def _is_mitred(self) -> bool:
        """Whether the corner is mitred where it isn't dovetailed."""
        return False

    def _corner(self) -> bd.Part:
        pins = self._pins(self._pin_length())
        if not self._is_mitred():
            return pins
        return pins + (self._mitre() & (self._block() - self._dovetailed()))

    def _dovetailed(self) -> bd.Part:
        """The part of the block where the boards are dovetailed."""
        x0, x1 = self._x_range(self._pin_length())
        start, stop = self._span()
        return bd.Pos(x0, start, -self.pins.part.thickness) * bd.Box(
            x1 - x0, stop - start, self._tail_length(), align=(bd.Align.MIN,) * 3
        )

    def _mitre(self) -> bd.Part:
        """The pin board's half of the block, mitred on its diagonal from the
        inside corner of the joint to the outside one."""
        pins, tails = self.parts()
        c, sign = self.pins.coordinate, self.pins.side.sign
        points = [(c, -pins.thickness), (c + sign * tails.thickness, 0), (c, 0)]
        # Drawn along the length (x) and the thickness (y) of the pin board, extruded across it.
        plane = bd.Plane((0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0))
        return bd.extrude(plane * bd.Polygon(*points), amount=pins.width, dir=(0, 1, 0))

    def _pin_profiles(self) -> list[list[tuple[float, float]]]:
        """Outlines of the pins (incl. half pins) as (across the width, along the normal).

        Pins are narrowest where the tails end (on the outside face of the
        pin board for through dovetails) and widest on its inside face
        (y = -thickness). Along the width the joint is laid out as:
        half pin | tail | pin | tail | ... | pin | tail | half pin
        """
        t = self.pins.part.thickness
        start, stop = self._span()
        top, bottom = self._tail_length() - t, -t
        flare = self._tail_length() / self.slope  # how far each sloped flank leans
        n = self.tail_count
        tail_wide = (stop - start - 2 * self.half_pin_width - (n - 1) * self.pin_width) / n
        if tail_wide - 2 * flare <= 0:
            raise ValueError("tails too narrow for this slope and pin width")

        u = start + self.half_pin_width
        profiles = [[(start, top), (start, bottom), (u + flare, bottom), (u, top)]]
        for _ in range(n - 1):
            u0 = u + tail_wide
            u1 = u0 + self.pin_width
            profiles.append([(u0, top), (u0 - flare, bottom), (u1 + flare, bottom), (u1, top)])
            u = u1
        u0 = u + tail_wide
        profiles.append([(u0, top), (u0 - flare, bottom), (stop, bottom), (stop, top)])
        return profiles


@dataclass
class MitredCornerDovetail(ThroughDovetail):
    """Through dovetails mitred at the edges of the corner, e.g. to hide a
    groove or a rabbet running along the inside of a box.

    At each of the pin board's edges in `mitred` (by default both), a strip
    `mitre_width` wide across the width is mitred through the whole
    thickness instead of dovetailed, so the edge of the corner shows a mitre
    and a groove or a rabbet within the strip runs through both boards
    unseen. The dovetails are laid out across the rest of the width, from a
    half pin next to each mitre. The boards must be equally wide.
    """

    mitred: tuple[SideRef, ...] | None = None
    mitre_width: float = 10.0

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.pins.part.width != self.tails.part.width:
            raise ValueError("the boards of a mitred dovetail must be equally wide")

    def with_defaults(self) -> Self:
        pins = self.pins.part
        mitred = self.mitred or (pins.front_edge, pins.back_edge)
        for edge in mitred:
            if edge.part is not pins or edge.axis != 1:
                raise ValueError(f"a dovetail is mitred at an edge of {pins.name}, not {edge}")
        return replace(self, mitred=mitred)

    def _mitred_at(self, side: Side) -> bool:
        return any(edge.side == side for edge in _require(self.mitred))

    def _span(self) -> Range:
        width, mitre = self.pins.part.width, self.mitre_width
        start = mitre if self._mitred_at(Side.FRONT_EDGE) else 0.0
        stop = width - mitre if self._mitred_at(Side.BACK_EDGE) else width
        return start, stop

    def _is_mitred(self) -> bool:
        return True

    def _descriptions(self) -> tuple[str, str]:
        sockets, dovetails = super()._descriptions()
        pins = self.pins.part
        edges = [side for side in (Side.FRONT_EDGE, Side.BACK_EDGE) if self._mitred_at(side)]
        tails = [_flush_side(self.tails.part, pins.side(side), self.placement()) for side in edges]
        mitre = f", mitred {self.mitre_width:g} mm at "
        return (
            sockets + mitre + ", ".join(str(pins.side(side)) for side in edges),
            dovetails + mitre + ", ".join(map(str, tails)),
        )


@dataclass
class HalfBlindDovetail(ThroughDovetail):
    """Half-blind dovetails, e.g. at the front of a drawer.

    Like through dovetails, but the tails stop short of the pin board's
    outside face, so it keeps a `lap` that hides them (by default a quarter
    of its thickness). The tails are as long as the sockets are deep.
    """

    lap: float | None = None

    def with_defaults(self) -> Self:
        return replace(self, lap=self.lap or rules.dovetail_lap(self.pins.part.thickness))

    def reach(self) -> float:
        lap = _require(self.lap)
        if not 0 < lap < self.pins.part.thickness:
            raise ValueError("the lap must be thinner than the pin board")
        return self.pins.part.thickness - lap

    def _descriptions(self) -> tuple[str, str]:
        n, depth = self.tail_count, self.reach()
        return (
            f"sockets for {n} half-blind dovetails, {depth:g} deep, lap {self.lap:g}",
            f"{n} half-blind dovetails, {depth:g} long, slope 1:{self.slope:g}",
        )


@dataclass
class BlindMitredDovetail(ThroughDovetail):
    """Blind mitred (secret mitre) dovetails, e.g. at the corners of a fine
    carcase: from outside the corner looks like a plain mitre.

    Both boards keep a lip at their outside face, mitred where they meet: the
    pin board one `lap` thick (by default a quarter of its thickness), the
    tail board one in proportion to its thickness, so that both lips meet the
    mitre at their inside corner. Behind the lips the tails and the pins
    interlock hidden, the tails as long as the pin board's sockets are deep
    and the pins stopping at the tail board's lip. At both edges a strip
    `mitre_width` wide is mitred through the whole thickness, so the edges
    show a mitre too; the dovetails are laid out between these strips, from a
    half pin next to each. The boards must be equally wide.
    """

    lap: float | None = None
    mitre_width: float = 10.0

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.pins.part.width != self.tails.part.width:
            raise ValueError("the boards of a mitred dovetail must be equally wide")

    def with_defaults(self) -> Self:
        return replace(self, lap=self.lap or rules.dovetail_lap(self.pins.part.thickness))

    def tail_lip(self) -> float:
        """The thickness of the tail board's lip, covering the ends of the pins."""
        pins, tails = self.parts()
        return _require(self.lap) * tails.thickness / pins.thickness

    def _tail_length(self) -> float:
        lap = _require(self.lap)
        if not 0 < lap < self.pins.part.thickness:
            raise ValueError("the lap must be thinner than the pin board")
        return self.pins.part.thickness - lap

    def _pin_length(self) -> float:
        return self.tails.part.thickness - self.tail_lip()

    def _span(self) -> Range:
        return self.mitre_width, self.pins.part.width - self.mitre_width

    def _is_mitred(self) -> bool:
        return True

    def _descriptions(self) -> tuple[str, str]:
        n = self.tail_count
        sockets, tails = round(self._tail_length(), 1), round(self._pin_length(), 1)
        return (
            f"sockets for {n} blind mitred dovetails, {sockets:g} deep, lap {self.lap:g}, "
            f"mitred {self.mitre_width:g} mm at the edges",
            f"{n} blind mitred dovetails, {sockets:g} long, slope 1:{self.slope:g}, "
            f"pins {tails:g} deep, lap {round(self.tail_lip(), 1):g}, "
            f"mitred {self.mitre_width:g} mm at the edges",
        )


@dataclass
class MitreCorner(Joint):
    """Two ends meeting at a right-angled corner, both mitred.

    `a_inside` and `b_inside` are the sides inside the corner: edges for a
    picture frame (mitre across the face), faces for a carcase (mitre across
    the edge). Design lengths are outside lengths, to the long points. The
    mitres meet on the diagonal of the corner: at 45 degrees for parts of
    equal width (or thickness, for a carcase).

    Two edges can meet the same way, mitred along the grain, the faces
    inside the corner: e.g. the boards of a hollow leg, a long L-shaped
    corner. Design widths are then outside widths; the left ends are flush.
    """

    a: SideRef
    b: SideRef
    a_inside: SideRef
    b_inside: SideRef
    flush: tuple[SideRef, SideRef] | None = None

    def parts(self) -> tuple[Board, Board]:
        return self.a.part, self.b.part

    def placement(self) -> bd.Location:
        a, b = self.parts()
        if self.a.axis == 2 or self.a.axis != self.b.axis:
            raise ValueError(
                f"a mitre corner joins two ends or two edges, not {self.a} and {self.b}"
            )
        if self.a.axis == 1:
            default = (a.left_end, b.left_end)
        elif self.a_inside.axis == 1:
            default = (a.ref_face, b.ref_face)
        else:
            default = (a.ref_edge, b.ref_edge)
        flush = self.flush or default
        # The end of b lies against the inside of a, moved out to a's outside.
        loc = mate(
            self.a_inside,
            self.b,
            flush=flush,
            position=flush_with(self.a),
            gap=-self.a_inside.depth,
        )
        if (_direction(loc, self.b_inside.normal) + self.a.normal).length > _EPS:
            raise ValueError(
                f"{self.b_inside} is not inside the corner; give the opposite side, "
                "or turn the part over with `flush`"
            )
        return loc

    def cuts(self, placement: bd.Location) -> list[Cut]:
        a_width, b_width = self.a_inside.depth, self.b_inside.depth
        return [
            Mitre(self.a, inside=self.a_inside, angle=math.degrees(math.atan2(b_width, a_width))),
            Mitre(self.b, inside=self.b_inside, angle=math.degrees(math.atan2(a_width, b_width))),
        ]


@dataclass
class MitredHalfLap(MitreCorner):
    """A corner half lap mitred on the show face, as on a frame: the front half
    of both parts is mitred, the back half lapped.

    Placed as `MitreCorner` (ends to the outside of the corner), with edges
    inside the corner. On `face` of part a (by default its reference face)
    and the face of part b flush with it, both parts are mitred `depth` deep
    (by default half their thickness), so the face shows a mitre; behind it
    part a keeps the whole corner, a lap, and part b is cut away there by an
    end rabbet, so the back shows a plain half lap. The mitre hides the end
    grain on the face, the lap gives the glue far more long-grain area than
    a plain mitre.
    """

    face: SideRef | None = None
    depth: float | None = None

    def __post_init__(self) -> None:
        if self.a_inside.axis != 1 or self.b_inside.axis != 1:
            raise ValueError("a mitred half lap has its edges inside the corner")

    def with_defaults(self) -> Self:
        a = self.a.part
        face = self.face or a.ref_face
        if face.part is not a or face.axis != 2:
            raise ValueError(f"a mitred half lap shows its mitre on a face of {a.name}")
        return replace(self, face=face, depth=self.depth or rules.lap_thickness(a.thickness))

    def cuts(self, placement: bd.Location) -> list[Cut]:
        face, depth = _require(self.face), _require(self.depth)
        b = self.b.part
        b_face = next(
            side
            for side in (b.top_face, b.bottom_face)
            if (_direction(placement, side.normal) - face.normal).length < _EPS
        )
        b_back = b.bottom_face if b_face == b.top_face else b.top_face
        mitre_a, mitre_b = (
            replace(mitre, face=side, depth=depth)
            for mitre, side in zip(super().cuts(placement), (face, b_face), strict=True)
        )
        lap = EndRabbet(b_back, at=self.b, width=self.a_inside.depth, depth=b.thickness - depth)
        return [mitre_a, mitre_b, lap]


@dataclass
class MitredFaceTenon(MitredHalfLap):
    """A frame corner mitred on the show face, with a hidden mortise and tenon
    behind the mitre (a mitred face tenon, as on a frame with a moulded or
    chamfered front).

    Placed as `MitreCorner` (ends to the outside of the corner, design
    lengths to the outside), with edges inside the corner. On `face` of part
    a (by default its reference face) and the face of part b flush with it,
    both parts are mitred `depth` deep (by default a third of their
    thickness), so the face shows a mitre. Behind it, part a (the stile)
    runs on square to the corner and part b (the rail) butts square against
    its inside edge, as in a plain mortise and tenon: b is cut back to that
    shoulder by an end rabbet, but for a tenon, which goes into a mortise in
    a's inside edge. The tenon lies in the layer behind the mitre, by
    default centered across it, `tenon_thickness` thick (by default a third
    or so of the layer) and `tenon_offset` below `face` if given. Across
    part b's width it keeps a `shoulder` at both edges (or a pair of them,
    at the front edge and at the back edge), by default a quarter of its
    width, so the mortise stays closed both towards the end of part a and
    at its inside edge. It is `tenon_length` long (by default two thirds of
    part a's width), so it doesn't show at the outer edge, and the mortise
    `clearance` deeper.
    """

    tenon_thickness: float | None = None
    tenon_length: float | None = None
    tenon_offset: float | None = None
    shoulder: float | tuple[float, float] | None = None
    clearance: float = 2.0

    def with_defaults(self) -> Self:
        a, b = self.parts()
        depth = self.depth or a.thickness / 3
        joint = super(MitredFaceTenon, replace(self, depth=depth)).with_defaults()
        layer = b.thickness - depth
        thickness = self.tenon_thickness or rules.tenon_thickness(layer)
        offset = depth + (layer - thickness) / 2 if self.tenon_offset is None else self.tenon_offset
        if not depth - _EPS <= offset <= b.thickness - thickness + _EPS:
            raise ValueError("the tenon lies in the layer behind the mitre")
        shoulder = self.shoulder
        if shoulder is None:
            shoulder = b.width / 4
        shoulders = (shoulder, shoulder) if isinstance(shoulder, int | float) else shoulder
        if min(shoulders) < _EPS or sum(shoulders) > b.width - _EPS:
            raise ValueError("a mitred face tenon has shoulders at both edges")
        length = self.tenon_length or rules.tenon_length(self.a_inside.depth)
        if not 0 < length <= self.a_inside.depth:
            raise ValueError(f"the tenon must not be longer than {a.name} is wide")
        return replace(
            joint,
            tenon_thickness=thickness,
            tenon_length=length,
            tenon_offset=offset,
            shoulder=shoulders,
        )

    def tenon_box(self, placement: bd.Location) -> tuple[Range, Range, Range]:
        """Ranges of the tenon in the frame of part b."""
        b = self.b.part
        shoulder = _require(self.shoulder)
        front, back = (shoulder, shoulder) if isinstance(shoulder, int | float) else shoulder
        sign = self.b.side.sign
        start = self.b.coordinate - sign * self.a_inside.depth  # at the shoulder
        x0, x1 = sorted((start, start + sign * _require(self.tenon_length)))
        thickness, offset = _require(self.tenon_thickness), _require(self.tenon_offset)
        # Below the face of b flush with `face`.
        normal = _direction(placement.inverse(), _require(self.face).normal)
        if normal.Z > 0:
            z = (-offset - thickness, -offset)
        else:
            z = (-b.thickness + offset, -b.thickness + offset + thickness)
        return (x0, x1), (front, b.width - back), z

    def cuts(self, placement: bd.Location) -> list[Cut]:
        mitre_a, mitre_b, lap = super().cuts(placement)
        assert isinstance(lap, EndRabbet)
        box = self.tenon_box(placement)
        b = self.b.part
        tenon = bd.Pos(*(r[0] for r in box)) * bd.Box(
            *(r[1] - r[0] for r in box), align=(bd.Align.MIN,) * 3
        )
        (x0, x1), (y0, y1), (z0, z1) = box
        description = (
            f"{lap.describe()}, leaving a tenon {y1 - y0:g} x {z1 - z0:g} mm, {x1 - x0:g} long"
        )
        rabbet = ShapeCut(b, lap.removal() - tenon, description)
        mortise = Pocket(self.a_inside, _socket(self.a_inside, placement, box, self.clearance))
        return [mitre_a, mortise, mitre_b, rabbet]


@dataclass
class MitreSplice(Joint):
    """Two parts end to end, lengthened by a mitre across both ends.

    `short` is the side of part a that the mitre shortens: an edge for a
    mitre across the face, a face for a mitre across the edge. The reference
    faces and edges of both parts are flush. Design lengths are to the long
    points, so the overall length is shorter by the overlap of the mitres.
    """

    a: SideRef
    b: SideRef
    short: SideRef
    angle: float = 45.0

    def parts(self) -> tuple[Board, Board]:
        return self.a.part, self.b.part

    def _mitre_a(self) -> Mitre:
        return Mitre(self.a, inside=self.short, angle=self.angle)

    def placement(self) -> bd.Location:
        a, b = self.parts()
        return mate(
            self.a,
            self.b,
            flush=(a.ref_face, b.ref_face),
            position=flush_with(a.ref_edge),
            gap=-self._mitre_a().shortening,
        )

    def cuts(self, placement: bd.Location) -> list[Cut]:
        # On part b the opposite side is short.
        b_short = next(
            side
            for side in map(self.b.part.side, Side)
            if (_direction(placement, side.normal) + self.short.normal).length < _EPS
        )
        return [self._mitre_a(), Mitre(self.b, inside=b_short, angle=self.angle)]


@dataclass
class CrossLap(Joint):
    """Two parts crossing each other, each with a dado where the other one crosses.

    Part b crosses part a at its edge `a`, with its end `b` first, and
    reaches `overhang` beyond a's other edge (by default the parts cross in
    their middles). The reference faces are flush; part a is cut `depth`
    deep from its reference face (by default half its thickness), part b
    from the other face, so b lies over a at the crossing.
    """

    a: SideRef
    b: SideRef
    position: Position = CENTERED
    overhang: float | None = None
    depth: float | None = None

    def parts(self) -> tuple[Board, Board]:
        return self.a.part, self.b.part

    def with_defaults(self) -> Self:
        a, b = self.parts()
        overhang = (b.length - self.a.depth) / 2 if self.overhang is None else self.overhang
        return replace(
            self, overhang=overhang, depth=self.depth or rules.lap_thickness(a.thickness)
        )

    def placement(self) -> bd.Location:
        a, b = self.parts()
        return mate(
            self.a,
            self.b,
            flush=(a.ref_face, b.ref_face),
            position=self.position,
            gap=-(self.a.depth + _require(self.overhang)),
        )

    def cuts(self, placement: bd.Location) -> list[Cut]:
        a, b = self.parts()
        depth = _require(self.depth)

        def crossing(side: SideRef, loc: bd.Location, other: Board, z: Range) -> Pocket:
            lo, hi = other.box
            box = list(_socket(side, loc, tuple(zip(lo, hi, strict=True)), 0.0))
            box[2] = z
            return Pocket(side, (box[0], box[1], box[2]))

        return [
            crossing(a.top_face, placement, b, (-depth, INF)),
            crossing(b.bottom_face, placement.inverse(), a, (-INF, -depth)),
        ]


@dataclass
class Button(Joint):
    """A wooden button holding a top down: a block screwed to the underside of
    the top, with a tongue at its end in a short mortise in the inside of an apron.

    The button's end `tongue` faces side `mortise` of the apron, `gap` away
    from it, and its top face is level with the apron's side `level` (its
    top edge, where the top lies); along the apron it is placed by
    `position`. The tongue is at the bottom of the button, `thickness`
    thick, and reaches `depth` into the apron. The mortise is `pull` higher
    than the tongue, so screwing the button pulls the top down onto the
    apron, `clearance` deeper, so the top can move towards the apron, and
    longer by `play` at either end, so it can move along it.
    """

    mortise: SideRef
    tongue: SideRef
    level: SideRef
    position: Position = CENTERED
    thickness: float = 6.0
    depth: float = 4.0
    gap: float = 2.0
    pull: float = 2.0
    clearance: float = 2.0
    play: float = 1.0

    def __post_init__(self) -> None:
        if self.tongue.axis != 0:
            raise ValueError(f"a button's tongue is on an end, not on {self.tongue}")
        if not 0 < self.thickness < self.tongue.part.thickness:
            raise ValueError("the tongue must be thinner than the button")

    def parts(self) -> tuple[Board, Board]:
        return self.mortise.part, self.tongue.part

    def tongue_cut(self) -> Tongue:
        button = self.tongue.part
        return Tongue(
            self.tongue,
            length=self.gap + self.depth,
            thickness=self.thickness,
            thickness_offset=button.thickness - self.thickness,
        )

    def allowances(self) -> list[Allowance]:
        return self.tongue_cut().allowances()

    def placement(self) -> bd.Location:
        return mate(
            self.mortise,
            self.tongue,
            flush=(self.level, self.tongue.part.top_face),
            position=self.position,
            gap=self.gap,
        )

    def cuts(self, placement: bd.Location) -> list[Cut]:
        tongue = self.tongue_cut()
        box = list(_socket(self.mortise, placement, tongue.tenon_box(), self.clearance))
        up, along = self.level.axis, 3 - self.mortise.axis - self.level.axis
        a, b = box[up]
        box[up] = (a, b + self.pull) if self.level.side.sign > 0 else (a - self.pull, b)
        a, b = box[along]
        box[along] = (a - self.play, b + self.play)
        return [Pocket(self.mortise, (box[0], box[1], box[2])), tongue]


def _flush_side(part: Board, side: SideRef, placement: bd.Location) -> SideRef:
    """The side of `part` (placed by `placement` in the frame of side's part) facing
    the same way as `side`."""
    return next(
        s
        for s in map(part.side, Side)
        if (_direction(placement, s.normal) - side.normal).length < _EPS
    )


def _axis(vector: bd.Vector) -> int:
    """The axis of the part frame a direction lies along."""
    return max(range(3), key=lambda axis: abs(tuple(vector)[axis]))


def _direction(loc: bd.Location, vector: bd.Vector) -> bd.Vector:
    """A direction mapped by a location (rotation only)."""
    return (loc * bd.Location(tuple(vector))).position - loc.position
