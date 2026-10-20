"""Stock: the material parts are made from."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Stock:
    """Stock of a given thickness (mm): a board, or a rod (`round`) as thick
    as its diameter. The grain runs along its length."""

    thickness: float
    species: str = ""
    round: bool = False

    @classmethod
    def board(cls, thickness: float, species: str = "") -> Stock:
        return cls(thickness=thickness, species=species)

    @classmethod
    def rod(cls, diameter: float, species: str = "") -> Stock:
        """Round stock: a dowel, a peg, a rung, a pole."""
        return cls(thickness=diameter, species=species, round=True)

    @property
    def diameter(self) -> float:
        if not self.round:
            raise ValueError("board stock has no diameter")
        return self.thickness
