"""Identical parts and cuts, for the cut list and the drawings: "4 x leg",
"24 x hole ø5".

Two parts are identical when they are of the same kind, from the same stock,
laminated the same way, with blanks of the same size, and the shape of one
is that of the other turned over in one of the ways a board can be: end for
end, face down or both, and for a square section (or a rod) also a quarter
turn about its length. The grain stays along the length. Which way round
doesn't matter: the woodworker picks the reference face and edge of each
piece as it comes.

When only a mirror image of one matches the other, they are a mirror pair
(opposite hand): the left and right sides of a drawer. They are grouped
too, the mirror images marked.

Cuts of a part are identical when they differ only in where they are (see
`Cut.offsets`): mortises described alike, holes but for their offsets.
"""

import itertools
import math
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import build123d as bd

from woodwright.cuts import Cut, Offset, describe_offsets
from woodwright.part import Board, Part, SideRef

if TYPE_CHECKING:
    from woodwright.assembly import ResolvedPart

Matrix3 = tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]

_EPS = 1e-6


@dataclass
class PartGroup:
    """Identical parts. The first is the one drawn and listed, the others
    are made the same, those in `mirrored` as its mirror image."""

    name: str
    parts: list[ResolvedPart]
    mirrored: list[ResolvedPart] = field(default_factory=list)

    @property
    def first(self) -> ResolvedPart:
        return self.parts[0]

    def __len__(self) -> int:
        return len(self.parts)

    def members(self) -> str:
        """The names of the parts, the mirror images after the others:
        'leg_1, leg_2; mirror image: leg_3, leg_4'."""
        same = ", ".join(p.part.name for p in self.parts if p not in self.mirrored)
        if not self.mirrored:
            return same
        return f"{same}; mirror image: {', '.join(p.part.name for p in self.mirrored)}"


def group_parts(parts: list[ResolvedPart]) -> list[PartGroup]:
    """The parts grouped into identical ones, in the order of their first
    parts, each group's parts in the given order (but a part not mirrored
    first)."""
    found: list[list[tuple[ResolvedPart, bool]]] = []  # parts, mirror image of the first
    for part in parts:
        for group in found:
            match = same_part(group[0][0], part)
            if match is not None:
                group.append((part, match))
                break
        else:
            found.append([(part, False)])

    ordered = []
    for group in found:
        # drawn as a part not mirrored by `Board(mirror=True)`, if there is one
        first = next((g for g in group if not g[0].part.mirror), group[0])
        ordered.append([first] + [g for g in group if g is not first])
    names = _group_names([[p.part.name for p, _ in group] for group in ordered])
    return [
        PartGroup(name, [p for p, _ in group], [p for p, m in group if m != group[0][1]])
        for name, group in zip(names, ordered, strict=True)
    ]


def _group_names(groups: list[list[str]]) -> list[str]:
    """Names for groups of parts, given by the names of their parts: the
    words they share (see `group_name`); groups that would share a name, or
    take one of a part not in them, with the words that tell their parts
    apart (`apron_front_back`, `apron_left_right`)."""
    base = [group_name(g) for g in groups]
    names = list(base)
    for i, (name, members) in enumerate(zip(base, groups, strict=True)):
        if len(members) == 1:
            continue
        clash = base.count(name) > 1 or any(
            name in other for j, other in enumerate(groups) if j != i
        )
        if clash:
            shared = name.split("_")
            rest = [w for n in members for w in n.split("_") if w not in shared]
            names[i] = "_".join([*shared, *dict.fromkeys(rest)])
    return [
        name if names.count(name) == 1 else members[0]
        for name, members in zip(names, groups, strict=True)
    ]


def group_name(names: list[str]) -> str:
    """The words of the names (between underscores) that all of them have,
    in order, but numbers: `leg` for `leg_front_left` and `back_right_leg`,
    `top_beam` for `top_beam_1` and `top_beam_2`. Without any, the names
    joined (`left_right`), or for more than three, the first."""
    words = [n.split("_") for n in names]
    common = [w for w in dict.fromkeys(words[0]) if all(w in ws for ws in words[1:])]
    common = [w for w in common if not w.isdigit()] if len(names) > 1 else common
    if common:
        return "_".join(common)
    return "_".join(names) if len(names) <= 3 else names[0]


def same_part(a: ResolvedPart, b: ResolvedPart) -> bool | None:
    """Whether part `b` is identical to `a` (False), its mirror image (True),
    or neither (None)."""
    pa, pb = a.part, b.part
    if type(pa) is not type(pb) or pa.stock != pb.stock:
        return None
    if isinstance(pa, Board) and (pa.plies, pa.plies_across) != (pb.plies, pb.plies_across):
        return None
    if any(abs(x - y) > _EPS for x, y in zip(a.size, b.size, strict=True)):
        return None
    sa, sb = _centred(a), _centred(b)
    volume = sa.volume
    if abs(volume - sb.volume) > _EPS * volume:
        return None
    centre = sa.center()
    laminated = isinstance(pa, Board) and pa.plies > 1
    for matrix, mirror in _turns(a.size, laminated):
        turned = _transformed(sb, matrix)
        if (turned.center() - centre).length > 1e-4:
            continue
        if abs((sa & turned).volume - volume) < _EPS * volume + 1e-3:
            return mirror
    return None


def _centred(part: ResolvedPart) -> bd.Part:
    """The part's shape with the centre of its blank at the origin."""
    lo, hi = part.blank
    return bd.Pos(*(-(x + y) / 2 for x, y in zip(lo, hi, strict=True))) * part.solid


def _turns(size: tuple[float, float, float], laminated: bool) -> list[tuple[Matrix3, bool]]:
    """The ways a blank of `size` maps onto itself, keeping its length along
    x, as matrices about its centre, and whether each mirrors it: the turns
    first, the identity first of all. Width and thickness swap only on a
    square section not glued up."""
    square = abs(size[1] - size[2]) < _EPS and not laminated
    turns = []
    for swap, (sx, sy, sz) in itertools.product(
        (False, True), itertools.product((1, -1), repeat=3)
    ):
        if swap and not square:
            continue
        rows = (
            ((sx, 0, 0), (0, 0, sy), (0, sz, 0)) if swap else ((sx, 0, 0), (0, sy, 0), (0, 0, sz))
        )
        mirror = sx * sy * sz * (-1 if swap else 1) < 0
        turns.append((rows, mirror))
    return sorted(turns, key=lambda t: t[1])


def _transformed(shape: bd.Part, matrix: Matrix3) -> bd.Part:
    """A shape turned or mirrored by an orthogonal matrix, exactly (keeping
    its planes and cylinders)."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.gp import gp_Trsf

    trsf = gp_Trsf()
    trsf.SetValues(*matrix[0], 0, *matrix[1], 0, *matrix[2], 0)
    return bd.Part(BRepBuilderAPI_Transform(shape.wrapped, trsf, True).Shape())


# --- Identical cuts -------------------------------------------------------------


def group_cuts(cuts: list[Cut]) -> list[list[Cut]]:
    """The cuts grouped into identical ones, in the order of the first of each."""
    groups: dict[tuple[type, str], list[Cut]] = {}
    for cut in cuts:
        groups.setdefault((type(cut), cut_shape(cut)), []).append(cut)
    return list(groups.values())


def cut_shape(cut: Cut) -> str:
    """A cut's description without where it lies, if it says so (a hole's offsets)."""
    return cut.describe() if cut.offsets() is None else cut.describe(at="")


def describe_cuts(cuts: list[Cut]) -> str:
    """Identical cuts as one: their count and description, and where they
    lie if they say so: as the rows and columns of a grid if they make one
    ('24 x hole ø5, ..., in b.top_face, 174 to 526 every 32 from b.left_end;
    37 from b.front_edge and b.back_edge'), else each position."""
    first = cuts[0]
    if len(cuts) == 1:
        return first.describe()
    if first.offsets() is None:
        return f"{len(cuts)} x {first.describe()}"
    return f"{len(cuts)} x {first.describe(at=_positions([c.offsets() for c in cuts]))}"


def _positions(offsets: list[tuple[Offset, ...]]) -> str:
    columns = [list(dict.fromkeys(column)) for column in zip(*offsets, strict=True)]
    if len(set(offsets)) == len(offsets) == math.prod(len(c) for c in columns):
        return "; ".join(_axis_positions(c) for c in columns)
    return "; ".join(describe_offsets(o) for o in offsets)


def _axis_positions(values: list[Offset]) -> str:
    """Positions along one axis: '55 and 305 from b.left_end', '37 from
    b.front_edge and b.back_edge', 'centered'."""
    by_ref: dict[SideRef, list[float]] = {}
    for value in filter(None, values):
        by_ref.setdefault(value[0], []).append(value[1])
    refs_by_numbers: dict[str, list[str]] = {}
    for ref, distances in by_ref.items():
        refs_by_numbers.setdefault(_numbers(distances), []).append(str(ref))
    phrases = [f"{numbers} from {' and '.join(refs)}" for numbers, refs in refs_by_numbers.items()]
    return ", ".join(phrases + (["centered"] if None in values else []))


def _numbers(values: list[float]) -> str:
    """'37', '55 and 305', '174 to 526 every 32' (evenly spaced), '10, 20 and 50'."""
    values = sorted({round(v, 6) for v in values})
    if len(values) == 1:
        return f"{values[0]:g}"
    steps = {round(b - a, 6) for a, b in itertools.pairwise(values)}
    if len(values) > 2 and len(steps) == 1:
        return f"{values[0]:g} to {values[-1]:g} every {steps.pop():g}"
    return ", ".join(f"{v:g}" for v in values[:-1]) + f" and {values[-1]:g}"


def local(text: str, part: Part) -> str:
    """A description with the part's sides named without the part, for a
    list under its name: 'in back_edge' for 'in stile.back_edge'."""
    return re.sub(rf"\b{re.escape(part.name)}\.", "", text)
