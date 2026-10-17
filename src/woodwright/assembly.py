"""Assemblies of parts and joints, and their resolution."""

from dataclasses import dataclass
from functools import cached_property

import build123d as bd

from woodwright.cuts import Cut
from woodwright.joints import Joint
from woodwright.part import Board, Point


class Assembly:
    """Parts and the joints between them. The first part added is the root."""

    def __init__(self, name: str, root_location: bd.Location | None = None) -> None:
        self.name = name
        self.root_location = root_location or bd.Location()
        self.parts: list[Board] = []
        self.joints: list[Joint] = []

    def add(self, part: Board) -> Board:
        raise NotImplementedError

    def join[J: Joint](self, joint: J) -> J:
        raise NotImplementedError

    def resolve(self) -> ResolvedModel:
        """Fill in joint defaults, size the blanks, place the parts, collect cuts."""
        raise NotImplementedError


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
        raise NotImplementedError

    @cached_property
    def shape(self) -> bd.Part:
        """Blank minus all cuts, in the part frame."""
        raise NotImplementedError

    @property
    def placed_shape(self) -> bd.Part:
        return self.location * self.shape


@dataclass
class ResolvedModel:
    name: str
    parts: list[ResolvedPart]
    joints: list[Joint]

    def __getitem__(self, part: Board) -> ResolvedPart:
        raise NotImplementedError

    def cut_list(self) -> str:
        raise NotImplementedError

    def compound(self) -> bd.Compound:
        """All parts placed in the assembly."""
        raise NotImplementedError
