import build123d as bd
import pytest

import woodwright as ww

OAK = ww.Stock.board(20, "oak")


def apply(loc: bd.Location, point: tuple) -> tuple:
    return tuple((loc * bd.Location(point)).position)


def direction(loc: bd.Location, vector: bd.Vector) -> tuple:
    return tuple(bd.Vector(apply(loc, tuple(vector))) - loc.position)


def stile_and_rail() -> tuple[ww.Board, ww.Board]:
    return (
        ww.Board("stile", OAK, length=600, width=60),
        ww.Board("rail", OAK, length=300, width=60),
    )


def test_mate_centered() -> None:
    stile, rail = stile_and_rail()
    loc = ww.mate(stile.back_edge, rail.left_end, flush=(stile.top_face, rail.top_face))

    # The middle of the rail's end lands in the middle of the stile's edge.
    assert apply(loc, (0, 30, -10)) == pytest.approx((300, 60, -10))
    # Mating sides face each other, flush sides face the same way.
    assert direction(loc, rail.left_end.normal) == pytest.approx(tuple(-stile.back_edge.normal))
    assert direction(loc, rail.top_face.normal) == pytest.approx(tuple(stile.top_face.normal))


def test_mate_with_offset() -> None:
    stile, rail = stile_and_rail()
    loc = ww.mate(
        stile.back_edge,
        rail.left_end,
        flush=(stile.top_face, rail.top_face),
        position=ww.offset(100),
    )
    # The stile's arris runs from its right end (right-hand rule), the rail's
    # from its front edge.
    assert apply(loc, (0, 0, 0)) == pytest.approx((500, 60, 0))
    assert apply(loc, (0, 60, 0)) == pytest.approx((440, 60, 0))


def test_mate_needs_flush_sides_adjacent_to_the_mating_sides() -> None:
    stile, rail = stile_and_rail()
    with pytest.raises(ValueError, match="not adjacent"):
        ww.mate(stile.back_edge, rail.left_end, flush=(stile.front_edge, rail.top_face))
    with pytest.raises(ValueError, match="not a side of"):
        ww.mate(stile.back_edge, rail.left_end, flush=(rail.top_face, rail.top_face))
