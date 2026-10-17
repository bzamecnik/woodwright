import build123d as bd
import pytest

import woodwright as ww

OAK = ww.Stock.board(20, "oak")


def bbox(shape: bd.Part) -> tuple[tuple, tuple]:
    box = shape.bounding_box()
    return pytest.approx(tuple(box.min)), pytest.approx(tuple(box.max))


def test_mortise_into_an_edge() -> None:
    stile = ww.Board("stile", OAK, length=600, width=60)
    mortise = ww.Mortise(stile.back_edge, start=275, length=50, offset=6, width=8, depth=42)
    removal = mortise.removal()

    assert removal.volume == pytest.approx(50 * 8 * 42)
    # The back edge's plane: x along the length, y down from the top face.
    lo, hi = bbox(removal)
    assert lo == (275, 18, -14)
    assert hi == (325, 60, -6)
    assert mortise.part is stile
    assert mortise.describe() == "mortise 50 x 8 mm, 42 deep, in stile.back_edge"


def test_centered_tenon_on_an_end() -> None:
    rail = ww.Board("rail", OAK, length=300, width=60)
    tenon = ww.Tenon(rail.left_end, length=40, thickness=8, width=50)

    lo, hi = bbox(tenon.tenon())
    assert lo == (-40, 5, -14)
    assert hi == (0, 55, -6)
    assert tenon.removal().volume == pytest.approx(40 * 60 * 20 - 40 * 50 * 8)
    assert tenon.describe() == "tenon 50 x 8 mm, 40 long, on rail.left_end"


def test_tenon_with_offsets() -> None:
    rail = ww.Board("rail", OAK, length=300, width=60)
    tenon = ww.Tenon(
        rail.right_end, length=30, thickness=10, width=40, width_offset=0, thickness_offset=2
    )
    # The right end's plane: x across the width, y up from the bottom face.
    lo, hi = bbox(tenon.tenon())
    assert lo == (300, 0, -18)
    assert hi == (330, 40, -8)


def test_shape_cut() -> None:
    board = ww.Board("b", OAK, length=100, width=50)
    box = bd.Box(10, 10, 10)
    cut = ww.ShapeCut(board, box, name="notch")
    assert cut.part is board
    assert cut.removal() is box
    assert cut.describe() == "notch"
