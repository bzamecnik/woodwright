"""Joints: relations between two parts that place them and cut both.

Most joints put one part (or a tenon on it) into a socket cut into the other
(`Housing`): the socket is derived from where the inserted part lands, so
the two fit by construction, and the cut list names it by its shape (dado,
rabbet, groove, mortise, ...).
"""

import functools
import math
import operator
from dataclasses import dataclass, replace
from typing import Self

import build123d as bd

from woodwright import rules
from woodwright.cuts import (
    INF,
    Allowance,
    Cut,
    DovetailTongue,
    Mitre,
    Pocket,
    Range,
    ShapeCut,
    SlotMortise,
    Tenon,
    Tongue,
)
from woodwright.part import Board, Side, SideRef
from woodwright.placement import CENTERED, FLUSH, Position, flush_with, mate, offset

__all__ = [
    "Allowance",
    "Bridle",
    "Butt",
    "Button",
    "CrossLap",
    "DadoJoint",
    "GrooveJoint",
    "HalfBlindDovetail",
    "HalfLap",
    "Housing",
    "Joint",
    "MitreCorner",
    "MitreSplice",
    "MitredShoulderTenon",
    "MortiseTenon",
    "RabbetJoint",
    "SlidingDovetail",
    "TeeBridle",
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
            pockets = [Pocket(socket, self.socket_box(placement, (box[0], box[1], box[2])))]
        else:
            pockets = [Pocket(socket, self.socket_box(placement, tenon.tenon_box()))]
            haunch = tenon.haunch_box()
            if haunch is not None:
                # Without clearance: as deep as the groove the haunch fills.
                haunch_socket = self.socket_box(placement, haunch, clearance=0.0)
                pockets.append(Pocket(socket, haunch_socket, kind="haunch mortise"))
        if tenon is None or not tenon.removes_material:
            return pockets
        return [*pockets, tenon]

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
    """

    socket: SideRef
    end: SideRef
    depth: float | None = None
    thickness: float | None = None
    slope: float = 7.0
    half: bool = False
    position: Position = CENTERED
    across: Position = FLUSH
    flush: tuple[SideRef, SideRef] | None = None
    clearance: float = 0.0

    def sides(self) -> tuple[SideRef, SideRef]:
        return self.socket, self.end

    def with_defaults(self) -> Self:
        return replace(
            self,
            depth=self.depth or rules.dado_depth(self.socket.depth),
            thickness=self.thickness or rules.dovetail_thickness(self.end.part.thickness),
        )

    def reach(self) -> float:
        return _require(self.depth)

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
        return [ShapeCut(self.socket.part, socket, description), tongue]


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
    """A tongue along an edge (or across an end) of part b in a groove in a side of part a.

    The boards' design widths are their visible faces; the tongue is added.
    It is centered across the thickness unless `tongue_offset` (from the
    reference face) is given: with 0 it is flush with the reference face,
    as on a drawer bottom rabbeted on its underside.
    """

    tongue: SideRef
    groove: SideRef
    tongue_thickness: float | None = None
    tongue_length: float | None = None
    tongue_offset: float | None = None
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
        return Tongue(
            self.tongue,
            length=self.reach(),
            thickness=_require(self.tongue_thickness),
            thickness_offset=self.tongue_offset,
        )


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
    across: Position = FLUSH
    flush: tuple[SideRef, SideRef] | None = None

    def sides(self) -> tuple[SideRef, SideRef]:
        return self.mortise, self.tenon

    def with_defaults(self) -> Self:
        haunch_length = self.haunch_length
        if self.haunch is not None and haunch_length is None:
            haunch_length = rules.groove_depth(self.mortise.part.thickness)
        return replace(
            self,
            tenon_thickness=self.tenon_thickness
            or rules.tenon_thickness(self.tenon.part.thickness),
            tenon_length=self.tenon_length or rules.tenon_length(self.mortise.depth),
            haunch_length=haunch_length,
        )

    def reach(self) -> float:
        return _require(self.tenon_length)

    def tenon_cut(self) -> Tenon:
        shoulder = self.shoulder
        front, back = (shoulder, shoulder) if isinstance(shoulder, int | float) else shoulder
        return Tenon(
            self.tenon,
            length=self.reach(),
            thickness=_require(self.tenon_thickness),
            width=self.tenon.size[0] - front - back,
            width_offset=front,
            thickness_offset=self.tenon_offset,
            haunch=self.haunch,
            haunch_length=self.haunch_length,
            mitre=self.mitre,
            chamfer=self.tenon_chamfer,
        )


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
        mortise = cuts[0]
        assert isinstance(mortise, Pocket)
        # The mortise is open to the notch, so cut it from the side.
        box = list(mortise.box)
        axis, (a, b) = self.mortise.axis, box[self.mortise.axis]
        box[axis] = (a, INF) if self.mortise.side.sign > 0 else (-INF, b)
        cuts[0] = replace(mortise, box=(box[0], box[1], box[2]))
        tenon = self.tenon_cut()
        mitred = _require(self.mitred)
        ends = {0: "", 1: ", mitred at one end", 2: ", mitred at both ends"}[len(mitred)]
        width = self.tenon.size[0]
        description = f"notch {width:g} long, {tenon.mitre_depth:g} deep{ends}, in {self.mortise}"
        notch = placement * tenon.reach_solid()
        return [*cuts, ShapeCut(self.mortise.part, notch, description)]


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
class ThroughDovetail(Joint):
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

    def parts(self) -> tuple[Board, Board]:
        return self.pins.part, self.tails.part

    def __post_init__(self) -> None:
        if self.pins.axis != 0 or self.tails.axis != 0:
            raise ValueError("dovetails are cut on the ends of boards")
        if self.pins.part.width > self.tails.part.width:
            raise ValueError("the pin board must not be wider than the tail board")

    def reach(self) -> float:
        """How far the tails reach into the pin board, from its inside face."""
        return self.pins.part.thickness

    def allowances(self) -> list[Allowance]:
        # The tails reach into the pin board, the pin board past the tail board.
        return [
            Allowance(self.tails, self.reach()),
            Allowance(self.pins, self.tails.part.thickness),
        ]

    def placement(self) -> bd.Location:
        # The tail board's end lies against the inside face of the pin board,
        # its outside face level with the end of the pin board's blank.
        pins, tails = self.parts()
        return mate(
            pins.bottom_face,
            self.tails,
            flush=self.flush or (pins.ref_edge, tails.ref_edge),
            position=offset(-tails.thickness, ref=self.pins),
        )

    def cuts(self, placement: bd.Location) -> list[Cut]:
        pins, tails = self.parts()
        # The block where the tails go, beyond the pin board's end, in its frame.
        c = self.pins.coordinate
        x0 = c if self.pins.side.sign > 0 else c - tails.thickness
        block = bd.Pos(x0, 0, -pins.thickness) * bd.Box(
            tails.thickness, pins.width, self.reach(), align=(bd.Align.MIN,) * 3
        )
        # Pin profiles are drawn across the width (x) and the thickness (y) of
        # the pin board and extruded along its length, through the tail board.
        profile_plane = bd.Plane((x0, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
        pin_solids = [
            bd.extrude(profile_plane * bd.Polygon(*points), amount=tails.thickness)
            for points in self._pin_profiles()
        ]
        pin_solid = functools.reduce(operator.add, pin_solids)
        sockets, dovetails = self._descriptions()
        return [
            ShapeCut(pins, block - pin_solid, sockets),
            ShapeCut(tails, placement.inverse() * pin_solid, dovetails),
        ]

    def _descriptions(self) -> tuple[str, str]:
        """Of the cuts on the pin board and on the tail board."""
        n = self.tail_count
        return f"sockets for {n} dovetails", f"{n} dovetails, slope 1:{self.slope:g}"

    def _pin_profiles(self) -> list[list[tuple[float, float]]]:
        """Outlines of the pins (incl. half pins) as (across the width, along the normal).

        Pins are narrowest where the tails end (on the outside face of the
        pin board for through dovetails) and widest on its inside face
        (y = -thickness). Along the width the joint is laid out as:
        half pin | tail | pin | tail | ... | pin | tail | half pin
        """
        t, width = self.pins.part.thickness, self.pins.part.width
        top, bottom = self.reach() - t, -t
        flare = self.reach() / self.slope  # how far each sloped flank leans
        n = self.tail_count
        tail_wide = (width - 2 * self.half_pin_width - (n - 1) * self.pin_width) / n
        if tail_wide - 2 * flare <= 0:
            raise ValueError("tails too narrow for this slope and pin width")

        u = self.half_pin_width
        profiles = [[(0, top), (0, bottom), (u + flare, bottom), (u, top)]]
        for _ in range(n - 1):
            u0 = u + tail_wide
            u1 = u0 + self.pin_width
            profiles.append([(u0, top), (u0 - flare, bottom), (u1 + flare, bottom), (u1, top)])
            u = u1
        u0 = u + tail_wide
        profiles.append([(u0, top), (u0 - flare, bottom), (width, bottom), (width, top)])
        return profiles


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
class MitreCorner(Joint):
    """Two ends meeting at a right-angled corner, both mitred.

    `a_inside` and `b_inside` are the sides inside the corner: edges for a
    picture frame (mitre across the face), faces for a carcase (mitre across
    the edge). Design lengths are outside lengths, to the long points. The
    mitres meet on the diagonal of the corner: at 45 degrees for parts of
    equal width (or thickness, for a carcase).
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
        flush = self.flush or (
            (a.ref_face, b.ref_face) if self.a_inside.axis == 1 else (a.ref_edge, b.ref_edge)
        )
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


def _direction(loc: bd.Location, vector: bd.Vector) -> bd.Vector:
    """A direction mapped by a location (rotation only)."""
    return (loc * bd.Location(tuple(vector))).position - loc.position
