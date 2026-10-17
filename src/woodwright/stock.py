"""Stock: the material parts are made from."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Stock:
    """Board stock of a given thickness (mm). The grain runs along its length."""

    thickness: float
    species: str = ""

    @classmethod
    def board(cls, thickness: float, species: str = "") -> Stock:
        return cls(thickness=thickness, species=species)
