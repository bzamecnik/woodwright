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


def test_mate_flush_with_a_side() -> None:
    stile, rail = stile_and_rail()
    flush = (stile.top_face, rail.top_face)
    # The rail's back edge faces the stile's left end, so it is flush with it.
    loc = ww.mate(
        stile.back_edge, rail.left_end, flush=flush, position=ww.flush_with(stile.left_end)
    )
    assert apply(loc, (0, 60, 0)) == pytest.approx((0, 60, 0))
    assert apply(loc, (0, 0, 0)) == pytest.approx((60, 60, 0))
    loc = ww.mate(
        stile.back_edge, rail.left_end, flush=flush, position=ww.offset(100, stile.right_end)
    )
    assert apply(loc, (0, 0, 0)) == pytest.approx((500, 60, 0))
    assert apply(loc, (0, 60, 0)) == pytest.approx((440, 60, 0))


def test_mate_offset_from_a_side_along_the_arris_only() -> None:
    stile, rail = stile_and_rail()
    with pytest.raises(ValueError, match="not a side at an end of the arris"):
        ww.mate(
            stile.back_edge,
            rail.left_end,
            flush=(stile.top_face, rail.top_face),
            position=ww.flush_with(stile.front_edge),
        )


def test_mate_across() -> None:
    stile = ww.Board("stile", ww.Stock.board(30), length=600, width=60)
    rail = ww.Board("rail", OAK, length=300, width=60)
    flush = (stile.top_face, rail.top_face)
    centered = ww.mate(stile.back_edge, rail.left_end, flush=flush, across=ww.centered())
    assert apply(centered, (0, 30, 0)) == pytest.approx((300, 60, -5))
    set_back = ww.mate(stile.back_edge, rail.left_end, flush=flush, across=ww.offset(2))
    assert apply(set_back, (0, 30, 0)) == pytest.approx((300, 60, -2))
