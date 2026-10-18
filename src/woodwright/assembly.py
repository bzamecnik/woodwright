"""Assemblies of parts and joints, and their resolution."""

from dataclasses import dataclass
from functools import cached_property
from typing import NamedTuple

import build123d as bd

from woodwright.cuts import Cut
from woodwright.joints import Joint
from woodwright.part import Board, Point
from woodwright.placement import Orientation


class Assembly:
    """Parts and the joints between them. The first part added is the root.

    The root is placed by `root_location`: an `Orientation` (see `orient`)
    or a build123d `Location` of its part frame.
    """

    def __init__(self, name: str, root_location: Orientation | bd.Location | None = None) -> None:
        self.name = name
        self.root_location = root_location or bd.Location()
        self.parts: list[Board] = []
        self.joints: list[Joint] = []

    def add(self, part: Board) -> Board:
        self.parts.append(part)
        return part

    def join[J: Joint](self, joint: J) -> J:
        self.joints.append(joint)
        return joint

    def resolve(self) -> ResolvedModel:
        """Fill in joint defaults, size the blanks, place the parts, collect cuts."""
        if not self.parts:
            raise ValueError(f"assembly {self.name} has no parts")
        joints = [joint.with_defaults() for joint in self.joints]
        for joint in joints:
            for part in joint.parts():
                if part not in self.parts:
                    raise ValueError(f"{part.name} is joined but not added to {self.name}")

        blanks = {part: (list(part.box[0]), list(part.box[1])) for part in self.parts}
        allowances = [a for joint in joints for a in joint.allowances()]
        allowances += [a for part in self.parts for cut in part.cuts for a in cut.allowances()]
        for allowance in allowances:
            lo, hi = blanks[allowance.side.part]
            axis = allowance.side.axis
            if allowance.side.side.sign > 0:
                hi[axis] += allowance.amount
            else:
                lo[axis] -= allowance.amount

        placements = [joint.placement() for joint in joints]
        # Each joint places part b relative to part a, and any separate pieces.
        links = []
        for joint, placement in zip(joints, placements, strict=True):
            a, b = joint.parts()
            links.append(_Link(joint, a, b, placement))
            for piece, location in joint.pieces(placement):
                if piece not in self.parts:
                    raise ValueError(f"{piece.name} is joined but not added to {self.name}")
                links.append(_Link(joint, a, piece, location))
        locations = self._place(links)

        cuts = {part: list(part.cuts) for part in self.parts}
        for joint, placement in zip(joints, placements, strict=True):
            for cut in joint.cuts(placement):
                cuts[cut.part].append(cut)

        parts = [
            ResolvedPart(part, (tuple(lo), tuple(hi)), cuts[part], locations[part])
            for part, (lo, hi) in blanks.items()
        ]
        return ResolvedModel(self.name, parts, joints)

    def _place(self, links: list[_Link]) -> dict[Board, bd.Location]:
        """Walk the joint graph from the root, then check joints closing loops."""
        root = self.parts[0]
        root_location = self.root_location
        if isinstance(root_location, Orientation):
            root_location = root_location.location(root)
        locations = {root: root_location}
        pending = list(range(len(links)))
        while pending:
            for i in pending:
                joint, a, b, placement = links[i]
                if a in locations and b in locations:
                    _check_loop(joint, a, b, locations[a] * placement, locations[b])
                elif a in locations:
                    locations[b] = locations[a] * placement
                elif b in locations:
                    locations[a] = locations[b] * placement.inverse()
                else:
                    continue
                pending.remove(i)
                break
            else:
                break  # no progress: the remaining joints are not connected to the root
        unplaced = [part.name for part in self.parts if part not in locations]
        if unplaced:
            raise ValueError(f"not connected to {root.name} by joints: {', '.join(unplaced)}")
        return locations


class _Link(NamedTuple):
    """Part b placed by a joint in the frame of part a."""

    joint: Joint
    a: Board
    b: Board
    placement: bd.Location


def _check_loop(
    joint: Joint, a: Board, b: Board, expected: bd.Location, actual: bd.Location
) -> None:
    points = [(0, 0, 0), (1000, 0, 0), (0, 1000, 0)]
    error = max(
        ((expected * bd.Location(p)).position - (actual * bd.Location(p)).position).length
        for p in points
    )
    if error > 1e-6:
        raise ValueError(
            f"{type(joint).__name__} between {a.name} and {b.name} doesn't close "
            f"the loop: off by up to {error:.3g} mm"
        )


@dataclass
class ResolvedPart:
    """A part with its blank, its cuts and its location in the assembly."""

    part: Board
    blank: tuple[Point, Point]  # min and max corners in the part frame
    cuts: list[Cut]
    location: bd.Location

    @property
    def size(self) -> tuple[float, float, float]:
        """Cut dimensions: length, width, thickness."""
        lo, hi = self.blank
        return hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]

    @cached_property
    def shape(self) -> bd.Part:
        """Blank minus all cuts, in the part frame."""
        lo = self.blank[0]
        shape = bd.Pos(*lo) * bd.Box(*self.size, align=(bd.Align.MIN,) * 3)
        for cut in self.cuts:
            shape -= cut.removal()
        shape.label = self.part.name
        return shape

    @property
    def placed_shape(self) -> bd.Part:
        shape = self.location * self.shape
        shape.label = self.part.name
        return shape


@dataclass
class ResolvedModel:
    name: str
    parts: list[ResolvedPart]
    joints: list[Joint]

    def __getitem__(self, part: Board) -> ResolvedPart:
        for resolved in self.parts:
            if resolved.part is part:
                return resolved
        raise KeyError(part.name)

    def cut_list(self) -> str:
        """Parts with their cut dimensions and the cuts made into them."""
        name_width = max(len(resolved.part.name) for resolved in self.parts)
        lines = []
        for resolved in self.parts:
            part = resolved.part
            size = " x ".join(f"{x:g}" for x in resolved.size)
            line = f"{part.name:<{name_width}}  {size} mm  {part.stock.species}".rstrip()
            lines.append(line + ", mirror image" if part.mirror else line)
            lines.extend(f"{'':<{name_width}}  - {cut.describe()}" for cut in resolved.cuts)
        return "\n".join(lines)

    def compound(self) -> bd.Compound:
        """All parts placed in the assembly."""
        return bd.Compound(label=self.name, children=[p.placed_shape for p in self.parts])
