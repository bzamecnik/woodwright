"""Cuts: material removed from a part, built in the part's frame.

Most cuts remove an axis-aligned box from a board (`BoxCut`): grooves, dados,
rabbets, mortises. They are described by ranges along the three axes of the
part frame, measured on the design box; an infinite bound means the cut is
open on that side (it runs out of the board), so it also goes through any
allowance there. The cut list names such cuts by their shape, whichever class
made them: a `Groove` at the very edge of a board is listed as a rabbet.
"""

import functools
import math
import operator
from dataclasses import dataclass

import build123d as bd

from woodwright.part import ArrisRef, Board, Side, SideRef

_MIN = (bd.Align.MIN, bd.Align.MIN, bd.Align.MIN)
_EPS = 1e-6
INF = math.inf

Range = tuple[float, float]


@dataclass(frozen=True)
class Allowance:
    """Extension of a part's blank beyond its design box at one side."""

    side: SideRef
    amount: float


class Cut:
    """Base class of cuts. Most cuts are made into one side of a part."""

    side: SideRef

    @property
    def part(self) -> Board:
        return self.side.part

    def removal(self) -> bd.Part:
        """The removed volume in the part frame."""
        raise NotImplementedError

    def allowances(self) -> list[Allowance]:
        """Extensions of the blank the cut needs, e.g. for a tenon."""
        return []

    def describe(self) -> str:
        return type(self).__name__


# --- Box cuts ---------------------------------------------------------------


class BoxCut(Cut):
    """A cut removing an axis-aligned box, given by ranges in the part frame."""

    def ranges(self) -> tuple[Range, Range, Range]:
        raise NotImplementedError

    def removal(self) -> bd.Part:
        return _box(self.part, self.ranges())

    def describe(self) -> str:
        return _describe_box(self.side, self.ranges())


@dataclass
class Pocket(BoxCut):
    """A box cut given directly by its ranges, e.g. a socket derived by a joint."""

    side: SideRef
    box: tuple[Range, Range, Range]
    kind: str | None = None  # the name in the cut list, instead of one from its shape

    def ranges(self) -> tuple[Range, Range, Range]:
        return self.box

    def describe(self) -> str:
        return _describe_box(self.side, self.box, self.kind)


@dataclass
class Groove(BoxCut):
    """A groove along the grain in a face or an edge, from end to end.

    It lies `distance` from `ref`, an adjacent side along the grain (by
    default the reference edge for faces and the reference face for edges),
    or in the middle when `distance` is None.
    """

    side: SideRef
    width: float
    depth: float
    distance: float | None = None
    ref: SideRef | None = None

    def __post_init__(self) -> None:
        if self.side.axis == 0:
            raise ValueError(f"a groove goes along the grain, not into {self.side}")
        if self.ref is None:
            board = self.side.part
            self.ref = board.ref_edge if self.side.axis == 2 else board.ref_face
        _check_adjacent(self.side, self.ref)
        if self.ref.axis == 0:
            raise ValueError(f"a groove is positioned from a side along the grain, not {self.ref}")

    def ranges(self) -> tuple[Range, Range, Range]:
        return _ranges(_into(self.side, self.depth), _across(self.ref, self.width, self.distance))


@dataclass
class Dado(BoxCut):
    """A dado across the grain in a face or an edge, from side to side.

    It lies `distance` from `ref`, an end (by default the left end), or in the
    middle when `distance` is None.
    """

    side: SideRef
    width: float
    depth: float
    distance: float | None = None
    ref: SideRef | None = None

    def __post_init__(self) -> None:
        if self.side.axis == 0:
            raise ValueError(f"a dado goes across the grain, not into {self.side}")
        if self.ref is None:
            self.ref = self.side.part.left_end
        if self.ref.part is not self.side.part or self.ref.axis != 0:
            raise ValueError(f"a dado is positioned from an end of {self.side.part.name}")

    def ranges(self) -> tuple[Range, Range, Range]:
        return _ranges(_into(self.side, self.depth), _across(self.ref, self.width, self.distance))


@dataclass
class Rabbet(BoxCut):
    """A rabbet into `side`, open to the adjacent side `at`, along their arris.

    `width` is measured on `side` from `at`, `depth` into `side`. With `at`
    an end it is an end rabbet.
    """

    side: SideRef
    at: SideRef
    width: float
    depth: float

    def __post_init__(self) -> None:
        _check_adjacent(self.side, self.at)

    def ranges(self) -> tuple[Range, Range, Range]:
        return _ranges(_into(self.side, self.depth), _into(self.at, self.width))


@dataclass
class EndRabbet(Rabbet):
    """A rabbet at an end of a board, across the grain."""

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.at.axis != 0:
            raise ValueError(f"an end rabbet is at an end, not at {self.at}")


@dataclass
class SlotMortise(BoxCut):
    """A slot into an end, open at the end and on two opposite sides.

    The slot lies `distance` from `ref` (by default the reference face, so the
    slot goes through the width), or in the middle when `distance` is None.
    """

    side: SideRef
    width: float
    depth: float
    distance: float | None = None
    ref: SideRef | None = None

    def __post_init__(self) -> None:
        if self.side.axis != 0:
            raise ValueError(f"a slot mortise goes into an end, not into {self.side}")
        if self.ref is None:
            self.ref = self.side.part.ref_face
        _check_adjacent(self.side, self.ref)

    def ranges(self) -> tuple[Range, Range, Range]:
        return _ranges(_into(self.side, self.depth), _across(self.ref, self.width, self.distance))


@dataclass
class Mortise(BoxCut):
    """A rectangular pocket into a side, in the side's plane coordinates.

    On a mirrored board it is mirrored: `start` is from its (named) left end.
    """

    side: SideRef
    start: float  # along the side's x
    length: float
    offset: float  # along the side's y
    width: float
    depth: float

    def ranges(self) -> tuple[Range, Range, Range]:
        box = side_box(
            self.side, self.start, self.offset, -self.depth, self.length, self.width, self.depth
        ).bounding_box()
        ranges = list(zip(box.min, box.max, strict=True))
        if self.part.mirror:
            a, b = ranges[0]
            ranges[0] = (self.part.length - b, self.part.length - a)
        return ranges[0], ranges[1], ranges[2]


# --- Tenons -----------------------------------------------------------------


@dataclass
class Tenon(Cut):
    """Shoulders and cheeks cut beyond a side (usually an end), leaving a tenon.

    The side is the shoulder plane; the material beyond it comes from an
    allowance the tenon asks for. Across the thickness the tenon lies
    `thickness_offset` below the top face; along the side (across the width
    for an end, along the length for an edge) `width_offset` from the front
    edge or the left end. Either is centered when None. Without `width` the
    tenon spans the whole side, with cheeks but no shoulders.

    With `haunch`, an edge (or an end) next to the side, the tenon has a
    haunch: a stub `haunch_length` long and as thick as the tenon, filling
    the shoulder towards that side, e.g. to fill a groove in the mortised part.

    With `mitre`, a face of the part, the end of the tenon is mitred at
    `mitre_angle` across its thickness: the cheek towards that face is
    shorter, the other one keeps the full length. Two tenons meeting inside
    a leg from adjacent sides are mitred like this so they don't clash.

    With `mitre_depth`, the shoulders are mitred: the part reaches that far
    beyond the side with its whole cross-section, into a notch in the
    mortised part, and the tenon starts there, `length` long. At each of
    `mitred`, edges next to the side, the reach is mitred at 45 degrees back
    to the side, so the parts meet on a short mitre at that edge. A tenon
    wider than the space between the mitres reaches under them: there the
    mitre is cut only down to its cheeks, the tenon starts at the side.

    With `chamfer`, the four arrises around the end of the tenon are
    chamfered at 45 degrees that wide, e.g. on a through tenon standing
    proud of the mortised part.
    """

    side: SideRef
    length: float
    thickness: float
    width: float | None = None
    width_offset: float | None = None
    thickness_offset: float | None = None
    haunch: SideRef | None = None
    haunch_length: float | None = None
    mitre: SideRef | None = None
    mitre_angle: float = 45.0
    mitre_depth: float = 0.0
    mitred: tuple[SideRef, ...] = ()
    chamfer: float = 0.0

    def __post_init__(self) -> None:
        if self.side.axis == 2:
            raise ValueError(f"a tenon is cut on an end or an edge, not on {self.side}")
        if self.chamfer:
            if self.mitre is not None:
                raise ValueError("a tenon is either mitred or chamfered at its end")
            if not 0 < self.chamfer < min(self.length, self.thickness / 2):
                raise ValueError("a tenon's chamfer must be thinner than half the tenon")
            if self.width is not None and self.chamfer >= self.width / 2:
                raise ValueError("a tenon's chamfer must be narrower than half the tenon")
        if self.mitre_depth < 0:
            raise ValueError("the mitred shoulders' depth must not be negative")
        for edge in self.mitred:
            _check_adjacent(self.side, edge)
            if edge.axis == 2:
                raise ValueError(f"a shoulder is mitred at an edge or an end, not at {edge}")
            if (
                self.mitre_depth
                > self.side.part.box[1][edge.axis] - self.side.part.box[0][edge.axis]
            ):
                raise ValueError("mitred shoulders must not be deeper than the part is wide")
        if self.mitre is not None:
            if self.mitre.part is not self.side.part or self.mitre.axis != 2:
                raise ValueError(f"a tenon is mitred towards a face, not towards {self.mitre}")
            if not 0 < self.mitre_angle < 90:
                raise ValueError("mitre angle must be between 0 and 90 degrees")
        if self.haunch is not None:
            _check_adjacent(self.side, self.haunch)
            if self.haunch.axis == 2:
                raise ValueError(f"a haunch reaches to an edge or an end, not to {self.haunch}")
            if self.width is None or self.haunch_length is None:
                raise ValueError("a haunched tenon needs a width and a haunch length")
            if not 0 < self.haunch_length <= self.length:
                raise ValueError("a haunch must not be longer than the tenon")

    def tenon_box(self) -> tuple[Range, Range, Range]:
        """Ranges of the tenon itself in the part frame."""
        lo, hi = self.part.box
        width_axis = 1 - self.side.axis  # across the width for ends, the length for edges
        boxes: dict[int, Range] = {
            self.side.axis: _beyond(self.side, self.length, start=self.mitre_depth)
        }
        t, offset = self.part.thickness, self.thickness_offset
        offset = (t - self.thickness) / 2 if offset is None else offset
        boxes[2] = (-offset - self.thickness, -offset)
        if self.width is None:
            boxes[width_axis] = (lo[width_axis], hi[width_axis])
        else:
            extent = hi[width_axis] - lo[width_axis]
            w_offset = (extent - self.width) / 2 if self.width_offset is None else self.width_offset
            if width_axis == 0 and self.part.mirror:  # from the left end, at x = length
                w_offset = extent - w_offset - self.width
            start = lo[width_axis] + w_offset
            boxes[width_axis] = (start, start + self.width)
        return boxes[0], boxes[1], boxes[2]

    def haunch_box(self) -> tuple[Range, Range, Range] | None:
        """Ranges of the haunch in the part frame, from the tenon to the `haunch` side."""
        if self.haunch is None or self.haunch_length is None:
            return None
        box = list(self.tenon_box())
        axis = self.haunch.axis
        a, b = box[axis]
        box[axis] = (
            (b, self.haunch.coordinate)
            if self.haunch.side.sign > 0
            else (
                self.haunch.coordinate,
                a,
            )
        )
        box[self.side.axis] = _beyond(self.side, self.haunch_length, start=self.mitre_depth)
        return box[0], box[1], box[2]

    def boxes(self) -> list[tuple[Range, Range, Range]]:
        """The tenon and its haunch, if any."""
        haunch = self.haunch_box()
        return [self.tenon_box()] if haunch is None else [self.tenon_box(), haunch]

    def tenon(self) -> bd.Part:
        """The tenon itself (with its haunch), in the part frame."""
        solid = _box(self.part, self.tenon_box())
        haunch = self.haunch_box()
        return solid if haunch is None else solid + _box(self.part, haunch)

    def removal(self) -> bd.Part:
        beyond = _ranges(_into(self.side, 0))
        removal = _box(self.part, beyond)
        # Open the tenon where it reaches the sides of the design box and the
        # end of the blank, so that no slivers are left between the boxes.
        # It starts at the side even with mitred shoulders, so where it
        # reaches under a mitre it isn't cut off by it.
        tenon = list(_open(self.part, self.tenon_box(), skip=self.side.axis))
        c = self.side.coordinate
        tenon[self.side.axis] = (c, INF) if self.side.side.sign > 0 else (-INF, c)
        removal -= _box(self.part, (tenon[0], tenon[1], tenon[2]))
        haunch = self.haunch_box()
        if haunch is not None:
            removal -= _box(self.part, _open(self.part, haunch, skip=self.side.axis))
        if self.mitre is not None:
            removal += self._mitre_removal() & _box(self.part, beyond)
        if self.chamfer:
            removal += self._chamfer_removal() & _box(self.part, beyond)
        if self.mitre_depth > 0:
            removal -= self.reach_solid()
        return removal

    def _chamfer_removal(self) -> bd.Part:
        """The four arrises around the end of the tenon, beyond the chamfers."""
        box = self.tenon_box()
        u, s, k = self.side.axis, self.side.side.sign, self.chamfer
        end = box[u][1] if s > 0 else box[u][0]
        m = _margin(self.part)
        corners = []
        for axis in (1 - u, 2):  # across the width, across the thickness
            for sign, c in zip((-1, 1), box[axis], strict=True):
                # As a `Chamfer` of the arris between the end and this side.
                points = [
                    (end, c - sign * k),
                    (end + s * m, c - sign * k),
                    (end + s * m, c + sign * m),
                    (end - s * k, c + sign * m),
                    (end - s * k, c),
                ]
                corners.append(_prism(self.part, u, axis, points))
        return functools.reduce(operator.add, corners)

    def reach_solid(self) -> bd.Part:
        """What the part reaches beyond the side before the tenon (with mitred
        shoulders), in the part frame, open behind the side and at the edges
        that aren't mitred, so that it doesn't leave slivers."""
        u, v = self.side.axis, 1 - self.side.axis
        c, s, d = self.side.coordinate, self.side.side.sign, self.mitre_depth
        lo, hi = self.part.box
        m = _margin(self.part)

        def corner(edge: float, inwards: int) -> list[tuple[float, float]]:
            if any(e.axis == v and e.side.sign == -inwards for e in self.mitred):
                return [(c - s * m, edge), (c, edge), (c + s * d, edge + inwards * d)]
            return [(c - s * m, edge - inwards * m), (c + s * d, edge - inwards * m)]

        points = corner(lo[v], +1) + corner(hi[v], -1)[::-1]
        if u == 1:
            points = [(q, p) for p, q in points]
        return _prism(self.part, 0, 1, points)

    def _mitre_removal(self) -> bd.Part:
        """The part of the tenon's end beyond the mitre, through the whole width."""
        assert self.mitre is not None
        (_, _), (_, _), (z0, z1) = self.tenon_box()
        inner, outer = (z1, z0) if self.mitre.side.sign > 0 else (z0, z1)
        c, s = self.side.coordinate + self.side.side.sign * self.mitre_depth, self.side.side.sign
        shortening = self.thickness * math.tan(math.radians(self.mitre_angle))
        long_point = (c + s * self.length, outer)
        short_point = (c + s * (self.length - shortening), inner)
        v = (short_point[0] - long_point[0], short_point[1] - long_point[1])
        p1 = (long_point[0] - v[0], long_point[1] - v[1])
        p2 = (short_point[0] + v[0], short_point[1] + v[1])
        out = s * (2 * shortening + _margin(self.part))
        points = [p1, p2, (p2[0] + out, p2[1]), (p1[0] + out, p1[1])]
        return _prism(self.part, self.side.axis, 2, points)

    def allowances(self) -> list[Allowance]:
        return [Allowance(self.side, self.mitre_depth + self.length)]

    def cheeks(self) -> int:
        """How many cheeks are cut: 0, 1 or 2."""
        t = self.part.thickness
        offset = self.thickness_offset
        offset = (t - self.thickness) / 2 if offset is None else offset
        return int(offset > _EPS) + int(offset + self.thickness < t - _EPS)

    @property
    def removes_material(self) -> bool:
        """False for a tenon as thick and wide as the part, e.g. a thin rail in a slot."""
        return self.cheeks() > 0 or self.width is not None

    def kind(self) -> str:
        cheeks = self.cheeks()
        if self.width is None:
            if cheeks == 1:
                return "lap"
            return "tongue" if self.side.axis == 1 else "tenon"
        return "barefaced tenon" if cheeks == 1 else "tenon"

    def describe(self) -> str:
        kind = self.kind()
        if self.width is None:
            return f"{kind} {self.thickness:g} mm thick, {self.length:g} long, on {self.side}"
        size = f"{self.width:g} x {self.thickness:g} mm, {self.length:g} long"
        if self.haunch is not None:
            kind = f"haunched {kind}"
            size += f", haunch {self.haunch_length:g} long"
        if self.mitre is not None:
            size += f", end mitred {self.mitre_angle:g} deg towards {self.mitre}"
        if self.chamfer:
            size += f", end chamfered {self.chamfer:g} mm"
        if self.mitre_depth > 0:
            reach = f", reaching {self.mitre_depth:g} beyond the shoulder"
            if self.mitred:
                edges = ", ".join(str(edge) for edge in self.mitred)
                reach += f", mitred at {edges}"
            size += reach
        return f"{kind} {size}, on {self.side}"


@dataclass
class Tongue(Tenon):
    """A tongue along an edge (or across an end): a tenon over the whole side,
    without shoulders.

    With a cheek only on one face (`thickness_offset` 0, or the tongue at
    the bottom face) it is listed as the rabbet that leaves it, e.g. the
    edges of a drawer bottom thinned to fit their grooves.
    """

    def __post_init__(self) -> None:
        if self.side.axis == 2:
            raise ValueError(f"a tongue is cut on an edge or an end, not on {self.side}")
        if self.width is not None:
            raise ValueError("a tongue runs along the whole side, it has no width")

    def kind(self) -> str:
        if self.cheeks() == 1:
            return "rabbet" if self.side.axis == 1 else "end rabbet"
        return "tongue"

    def describe(self) -> str:
        if self.cheeks() != 1:
            return super().describe()
        (_, _), (_, _), (z0, _) = self.tenon_box()
        face = self.part.bottom_face if z0 > -self.part.thickness + _EPS else self.part.top_face
        depth = self.part.thickness - self.thickness
        return f"{self.kind()} {self.length:g} mm, {depth:g} deep, in {face} at {self.side}"


@dataclass
class DovetailTongue(Cut):
    """A dovetail-shaped tongue beyond an end (or an edge), for a sliding dovetail.

    The tongue runs along the whole side. It is `thickness` thick at the
    shoulder, `thickness_offset` below the top face (centered when None), and
    its cheeks flare outwards by 1:`slope`; with `half` only the bottom one.
    Like a tenon, it asks for an allowance of its length.
    """

    side: SideRef
    length: float
    thickness: float
    slope: float = 7.0
    thickness_offset: float | None = None
    half: bool = False

    def __post_init__(self) -> None:
        if self.side.axis == 2:
            raise ValueError(f"a dovetail tongue is cut on an end or an edge, not on {self.side}")

    def solid(self, back: float = 0.0, beyond: float = 0.0) -> bd.Part:
        """The tongue in the part frame, its cheeks extended `back` behind the
        shoulder and `beyond` its end (e.g. for the socket's clearance)."""
        side = self.side
        t = self.part.thickness
        offset = (
            (t - self.thickness) / 2 if self.thickness_offset is None else self.thickness_offset
        )
        c, s = side.coordinate, side.side.sign

        def cheeks(d: float) -> tuple[float, float]:
            """z of the top and bottom cheek, at distance d beyond the shoulder."""
            flare = d / self.slope
            top = -offset + (0 if self.half else flare)
            return top, -offset - self.thickness - flare

        points = []
        for d in (-back, self.length + beyond):
            top, bottom = cheeks(d)
            points.extend([(c + s * d, top), (c + s * d, bottom)])
        points[2:] = points[:1:-1]  # around the outline
        return _prism(self.part, side.axis, 2, points)

    def removal(self) -> bd.Part:
        return _box(self.part, _ranges(_into(self.side, 0))) - self.solid()

    def allowances(self) -> list[Allowance]:
        return [Allowance(self.side, self.length)]

    def describe(self) -> str:
        kind = "half dovetail tongue" if self.half else "dovetail tongue"
        return (
            f"{kind} {self.thickness:g} mm at the shoulder, {self.length:g} long, "
            f"1:{self.slope:g}, on {self.side}"
        )


# --- Angled cuts ------------------------------------------------------------


@dataclass
class Chamfer(Cut):
    """A chamfer along an arris, `size` wide on its first side, `size_b` on the second.

    With `size_b` None the chamfer is at 45 degrees.
    """

    arris: ArrisRef
    size: float
    size_b: float | None = None

    @property
    def part(self) -> Board:
        return self.arris.a.part

    def removal(self) -> bd.Part:
        a, b = self.arris.a, self.arris.b
        size_b = self.size if self.size_b is None else self.size_b
        m = _margin(self.part)
        sa, sb = a.side.sign, b.side.sign
        ca, cb = a.coordinate, b.coordinate
        # Corner region in the (a.axis, b.axis) plane, beyond the chamfer line.
        points = [
            (ca, cb - sb * self.size),
            (ca + sa * m, cb - sb * self.size),
            (ca + sa * m, cb + sb * m),
            (ca - sa * size_b, cb + sb * m),
            (ca - sa * size_b, cb),
        ]
        return _prism(self.part, a.axis, b.axis, points)

    def describe(self) -> str:
        size_b = "" if self.size_b is None else f" x {self.size_b:g}"
        return f"chamfer {self.size:g}{size_b} mm on {self.arris}"


@dataclass
class Mitre(Cut):
    """An end cut at `angle` from square, shortening the `inside` side.

    The opposite side keeps the full design length (the long point), so the
    design length is the outside length, as for a picture frame. With
    `inside` an edge the mitre is across the face (picture frame), with
    `inside` a face it is across the edge (carcase corner).
    """

    side: SideRef
    inside: SideRef
    angle: float = 45.0

    def __post_init__(self) -> None:
        if self.side.axis != 0:
            raise ValueError(f"a mitre is cut on an end, not on {self.side}")
        _check_adjacent(self.side, self.inside)
        if not 0 < self.angle < 90:
            raise ValueError(f"mitre angle must be between 0 and 90 degrees, got {self.angle}")

    @property
    def shortening(self) -> float:
        """How much shorter the inside side is than the design length."""
        return self.inside.depth * math.tan(math.radians(self.angle))

    def removal(self) -> bd.Part:
        end, inside = self.side, self.inside
        lo, hi = self.part.box
        e, a = end.axis, inside.axis
        se = end.side.sign
        ce, ci = end.coordinate, inside.coordinate
        co = (lo if inside.side.sign > 0 else hi)[a]  # the opposite side
        long_point = (ce, co)
        short_point = (ce - se * self.shortening, ci)
        v = (short_point[0] - long_point[0], short_point[1] - long_point[1])
        p1 = (long_point[0] - v[0], long_point[1] - v[1])
        p2 = (short_point[0] + v[0], short_point[1] + v[1])
        out = se * (2 * self.shortening + _margin(self.part))
        points = [p1, p2, (p2[0] + out, p2[1]), (p1[0] + out, p1[1])]
        return _prism(self.part, e, a, points)

    def describe(self) -> str:
        return f"mitre {self.angle:g} deg on {self.side}, {self.inside} inside"


@dataclass
class Taper(Cut):
    """A face or an edge planed at a slope, so that the part is `amount` thinner
    (or narrower) at `end` than at the start of the taper.

    The taper starts `length` from `end` (by default at the other end).
    """

    side: SideRef
    end: SideRef
    amount: float
    length: float | None = None

    def __post_init__(self) -> None:
        if self.side.axis == 0:
            raise ValueError(f"a taper is planed on a face or an edge, not on {self.side}")
        if self.end.part is not self.side.part or self.end.axis != 0:
            raise ValueError(f"a taper runs towards an end of {self.side.part.name}")
        if not 0 < self.amount < self.side.depth:
            raise ValueError(f"taper amount must be between 0 and {self.side.depth:g}")

    def removal(self) -> bd.Part:
        side, end = self.side, self.end
        length = self.part.length if self.length is None else self.length
        s, c = side.side.sign, side.coordinate
        x1 = end.coordinate
        x0 = x1 - end.side.sign * length
        start, stop = (x0, c), (x1, c - s * self.amount)
        v = (stop[0] - start[0], stop[1] - start[1])
        p1 = (start[0] - v[0], start[1] - v[1])
        p2 = (stop[0] + v[0], stop[1] + v[1])
        out = s * (2 * self.amount + _margin(self.part))
        # Beyond the sloped line, but not before the start of the taper.
        points = [(x0, c), p2, (p2[0], p2[1] + out), (x0, c + out)]
        if self.length is None:
            points = [p1, p2, (p2[0], p2[1] + out), (p1[0], p1[1] + out)]
        return _prism(self.part, 0, side.axis, points)

    def describe(self) -> str:
        over = "" if self.length is None else f" over {self.length:g}"
        return f"taper {self.amount:g} mm{over} on {self.side} towards {self.end}"


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


# --- Helpers ----------------------------------------------------------------


def _check_adjacent(side: SideRef, other: SideRef) -> None:
    if other.part is not side.part or other.axis == side.axis:
        raise ValueError(f"{other} is not adjacent to {side}")


def _into(side: SideRef, depth: float) -> tuple[int, Range]:
    """From `side` into the part by `depth`, open outwards."""
    c = side.coordinate
    return side.axis, ((c - depth, INF) if side.side.sign > 0 else (-INF, c + depth))


def _beyond(side: SideRef, length: float, start: float = 0.0) -> Range:
    """From `start` beyond `side` outwards by `length`."""
    c = side.coordinate + side.side.sign * start
    return (c, c + length) if side.side.sign > 0 else (c - length, c)


def _across(ref: SideRef, width: float, distance: float | None) -> tuple[int, Range]:
    """`width` wide, `distance` from `ref` inwards, or centered when None."""
    lo, hi = ref.part.box
    axis = ref.axis
    if distance is None:
        distance = (hi[axis] - lo[axis] - width) / 2
    c = ref.coordinate
    if ref.side.sign > 0:
        return axis, (c - distance - width, c - distance)
    return axis, (c + distance, c + distance + width)


def _ranges(*given: tuple[int, Range]) -> tuple[Range, Range, Range]:
    """Ranges on the given axes, the others through the whole part."""
    ranges = [(-INF, INF)] * 3
    for axis, r in given:
        ranges[axis] = r
    return ranges[0], ranges[1], ranges[2]


def _open(
    part: Board, ranges: tuple[Range, Range, Range], skip: int | None = None
) -> tuple[Range, Range, Range]:
    """Make bounds open where they reach the sides of the design box."""
    lo, hi = part.box
    opened = []
    for axis, (a, b) in enumerate(ranges):
        if axis != skip:
            a = -INF if a <= lo[axis] + _EPS else a
            b = INF if b >= hi[axis] - _EPS else b
        opened.append((a, b))
    return opened[0], opened[1], opened[2]


def _margin(part: Board) -> float:
    """How far open cuts reach beyond the design box (to clear any allowance)."""
    return part.length + part.width + part.thickness


def _box(part: Board, ranges: tuple[Range, Range, Range]) -> bd.Part:
    lo, hi = part.box
    m = _margin(part)
    corner, size = [], []
    for axis, (a, b) in enumerate(ranges):
        a = lo[axis] - m if a == -INF else a
        b = hi[axis] + m if b == INF else b
        corner.append(a)
        size.append(b - a)
    return bd.Pos(*corner) * bd.Box(*size, align=_MIN)


def _unit(axis: int) -> bd.Vector:
    coords = [0.0, 0.0, 0.0]
    coords[axis] = 1.0
    return bd.Vector(*coords)


def _prism(part: Board, i: int, j: int, points: list[tuple[float, float]]) -> bd.Part:
    """A polygon in (i, j) coordinates of the part frame, through the part along the third axis."""
    t = 3 - i - j
    lo, hi = part.box
    origin = [0.0, 0.0, 0.0]
    origin[t] = (lo[t] + hi[t]) / 2
    x_dir, y_dir = _unit(i), _unit(j)
    plane = bd.Plane(tuple(origin), x_dir=x_dir, z_dir=x_dir.cross(y_dir))
    face = plane * bd.Polygon(*points)
    return bd.extrude(face, amount=(hi[t] - lo[t]) / 2 + _margin(part), both=True)


def _describe_box(
    side: SideRef, ranges: tuple[Range, Range, Range], kind: str | None = None
) -> str:
    """Name a box cut by its shape, with its sizes, e.g. 'groove 10 mm, 5 deep, in b.top_face'."""
    part = side.part
    lo, hi = part.box
    # How each axis is open: both ways, one way (to which side), or not at all.
    full, open_sides, closed = set(), {}, set()
    for axis, (a, b) in enumerate(_open(part, ranges)):
        if a == -INF and b == INF:
            full.add(axis)
        elif a == -INF:
            open_sides[axis] = SideRef(part, _side(axis, -1))
        elif b == INF:
            open_sides[axis] = SideRef(part, _side(axis, +1))
        else:
            closed.add(axis)

    # The side the cut is entered from: the given one if open, else a face,
    # an edge or an end the cut is open to.
    if side.axis in open_sides:
        entry_axis = side.axis
    elif open_sides:
        entry_axis = max(open_sides)
    else:
        entry_axis = side.axis
    entry = open_sides.get(entry_axis, side)
    others = [s for axis, s in sorted(open_sides.items()) if axis != entry_axis]

    if len(full) == 3:
        name = "removal"
    elif len(full) == 2:
        name = "recess"
    elif len(full) == 1 and not others:
        (along,) = full
        if along == entry_axis:
            name = "through mortise"
        elif entry_axis not in open_sides:
            name = "notch"
        elif along == 0:
            name = "groove"
        elif entry_axis == 0:
            name = "slot mortise"
        else:
            name = "dado"
    elif len(full) == 1:
        name = "rabbet" if full == {0} else "end rabbet"
    elif not others and entry_axis in open_sides:
        name = "mortise"
    else:
        name = "notch"

    name = kind or name

    def extent(axis: int) -> float:
        a, b = ranges[axis]
        return min(b, hi[axis]) - max(a, lo[axis])

    sizes = " x ".join(f"{extent(axis):g}" for axis in entry._plane_axes if axis not in full)
    text = f"{name} {sizes} mm" if sizes else name
    if entry_axis not in full:
        text += f", {extent(entry_axis):g} deep,"
    text += f" in {entry}"
    if others:
        text += " at " + ", ".join(str(s) for s in others)
    return text


def _side(axis: int, sign: int) -> Side:
    return next(s for s in Side if s.axis == axis and s.sign == sign)
