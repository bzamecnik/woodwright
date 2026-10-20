import math

import build123d as bd
import pytest

import woodwright as ww
from woodwright import Side

OAK = ww.Stock.board(20, "oak")


def make_board() -> ww.Board:
    return ww.Board("b", OAK, length=300, width=60)


def approx_vec(v: bd.Vector) -> tuple:
    return pytest.approx(tuple(v))


def test_design_box() -> None:
    assert make_board().box == ((0, 0, -20), (300, 60, 0))


@pytest.mark.parametrize(
    ("side", "normal"),
    [
        (Side.TOP_FACE, (0, 0, 1)),
        (Side.BOTTOM_FACE, (0, 0, -1)),
        (Side.FRONT_EDGE, (0, -1, 0)),
        (Side.BACK_EDGE, (0, 1, 0)),
        (Side.LEFT_END, (-1, 0, 0)),
        (Side.RIGHT_END, (1, 0, 0)),
    ],
)
def test_side_normal_points_out(side: Side, normal: tuple) -> None:
    assert tuple(make_board().side(side).normal) == approx_vec(bd.Vector(normal))


@pytest.mark.parametrize(
    ("side", "size", "depth"),
    [
        (Side.TOP_FACE, (300, 60), 20),
        (Side.BOTTOM_FACE, (300, 60), 20),
        (Side.FRONT_EDGE, (300, 20), 60),
        (Side.BACK_EDGE, (300, 20), 60),
        (Side.LEFT_END, (60, 20), 300),
        (Side.RIGHT_END, (60, 20), 300),
    ],
)
def test_side_size_and_depth(side: Side, size: tuple, depth: float) -> None:
    s = make_board().side(side)
    assert s.size == size
    assert s.depth == depth


@pytest.mark.parametrize("side", list(Side))
def test_side_plane_covers_the_side(side: Side) -> None:
    board = make_board()
    s = board.side(side)
    plane = s.plane
    assert tuple(plane.z_dir) == approx_vec(s.normal)

    lo, hi = board.box
    bound = (hi if side.sign > 0 else lo)[side.axis]
    u, v = s.size
    for x in (0, u):
        for y in (0, v):
            corner = tuple(plane.from_local_coords((x, y, 0)))
            assert corner[side.axis] == pytest.approx(bound)
            for axis in range(3):
                assert lo[axis] - 1e-9 <= corner[axis] <= hi[axis] + 1e-9


def test_reference_sides() -> None:
    board = make_board()
    assert board.ref_face == board.top_face
    assert board.ref_edge == board.front_edge
    assert str(board.ref_face) == "b.top_face"


def test_reference_arris_runs_along_the_length() -> None:
    p0, p1 = make_board().ref_arris.endpoints
    assert tuple(p0) == approx_vec(bd.Vector(0, 0, 0))
    assert tuple(p1) == approx_vec(bd.Vector(300, 0, 0))


def test_arris_across_an_end() -> None:
    board = make_board()
    p0, p1 = board.arris(board.right_end, board.bottom_face).endpoints
    assert tuple(p0) == approx_vec(bd.Vector(300, 0, -20))
    assert tuple(p1) == approx_vec(bd.Vector(300, 60, -20))


def test_arris_needs_adjacent_sides() -> None:
    board = make_board()
    with pytest.raises(ValueError, match="not adjacent"):
        board.arris(board.top_face, board.bottom_face)
    with pytest.raises(ValueError, match="not adjacent"):
        board.arris(board.top_face, make_board().front_edge)


def test_explicit_cut() -> None:
    board = make_board()
    cut = ww.ShapeCut(board, bd.Box(1, 1, 1))
    assert board.cut(cut) is cut
    assert board.cuts == [cut]


def test_mirrored_board_swaps_the_names_of_its_ends() -> None:
    board = ww.Board("b", OAK, length=300, width=60, mirror=True)
    assert board.left_end.side is Side.RIGHT_END
    assert board.side(Side.LEFT_END) == board.left_end
    assert board.left_end.coordinate == 300
    assert str(board.left_end) == "b.left_end"
    assert str(board.arris(board.top_face, board.right_end)) == "b.top_face_right_end_arris"
    # Faces and edges are not affected.
    assert board.ref_edge.side is Side.FRONT_EDGE


@pytest.mark.parametrize(
    "cut",
    [
        lambda b: ww.Dado(b.top_face, width=20, depth=5, distance=40),
        lambda b: ww.EndRabbet(b.top_face, at=b.left_end, width=20, depth=5),
        lambda b: ww.Mortise(b.back_edge, start=50, length=40, offset=6, width=8, depth=20),
        lambda b: ww.Tenon(b.front_edge, length=10, thickness=8, width=50, width_offset=30),
        lambda b: ww.Taper(b.top_face, end=b.left_end, amount=5, length=100),
        lambda b: ww.Hole(b.top_face, 8, depth=10, at={b.left_end: 30, b.front_edge: 15}),
    ],
)
def test_cuts_on_a_mirrored_board_are_mirrored(cut) -> None:
    def shape(mirror: bool) -> bd.Part:
        asm = ww.Assembly("a")
        board = asm.add(ww.Board("b", OAK, length=300, width=60, mirror=mirror))
        board.cut(cut(board))
        return asm.resolve()[board].shape

    plain, mirrored = shape(False), shape(True)
    reflected = bd.mirror(plain, bd.Plane.YZ.offset(150))
    assert mirrored.volume == pytest.approx(plain.volume)
    assert (mirrored - reflected).volume == pytest.approx(0, abs=1e-6)


ROD = ww.Stock.rod(30, "oak")


def test_rod_stock() -> None:
    assert ROD.diameter == 30
    assert ROD.round
    with pytest.raises(ValueError, match="no diameter"):
        _ = OAK.diameter


def test_rod_is_a_box_with_virtual_long_sides() -> None:
    rod = ww.Rod("rung", ROD, length=400)
    assert isinstance(rod, ww.Part)
    assert rod.box == ((0, 0, -30), (400, 30, 0))
    assert rod.width == rod.thickness == rod.diameter == 30
    assert rod.axis == (15, -15)
    assert not rod.left_end.virtual
    assert all(s.virtual for s in (rod.top_face, rod.bottom_face, rod.front_edge, rod.back_edge))
    assert not make_board().top_face.virtual


def test_rod_blank_is_a_cylinder() -> None:
    rod = ww.Rod("rung", ROD, length=400)
    blank = rod.blank((-20, 0, -30), (400, 30, 0))
    assert blank.volume == pytest.approx(math.pi * 15**2 * 420)
    box = blank.bounding_box()
    assert tuple(box.min) == pytest.approx((-20, 0, -30), abs=1e-6)
    assert tuple(box.max) == pytest.approx((400, 30, 0), abs=1e-6)


def test_stock_must_match_the_part() -> None:
    with pytest.raises(ValueError, match="make it a Rod"):
        ww.Board("b", ROD, length=300, width=30)
    with pytest.raises(ValueError, match="use Stock"):
        ww.Rod("r", OAK, length=300)
