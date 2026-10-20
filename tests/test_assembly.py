"""Resolving assemblies, checked against the plain build123d versions of the examples."""

import math

import build123d as bd
import pytest

import woodwright as ww

OAK = ww.Stock.board(20, "oak")


def bbox(shape: bd.Shape) -> tuple:
    box = shape.bounding_box()
    return pytest.approx((*box.min, *box.max), abs=1e-6)


def interference(a: bd.Part, b: bd.Part) -> float:
    overlap = a.intersect(b)
    return _volume(overlap)


def mortise_tenon() -> tuple[ww.Assembly, ww.Board, ww.Board]:
    asm = ww.Assembly("mortise_tenon", root_location=ww.orient(right_end=ww.UP, back_edge=ww.RIGHT))
    stile = asm.add(ww.Board("stile", OAK, length=600, width=60))
    rail = asm.add(ww.Board("rail", OAK, length=300, width=60))
    asm.join(ww.MortiseTenon(tenon=rail.left_end, mortise=stile.back_edge))
    return asm, stile, rail


def dovetail_corner() -> tuple[ww.Assembly, ww.Board, ww.Board]:
    # Side standing up (length along Z), its reference face outside at x = 0,
    # placed by a raw build123d location of its part frame.
    asm = ww.Assembly(
        "dovetail_corner",
        root_location=bd.Location(bd.Plane((0, 0, 0), x_dir=(0, 0, 1), z_dir=(-1, 0, 0))),
    )
    side = asm.add(ww.Board("side", OAK, length=380, width=200))
    top = asm.add(ww.Board("top", OAK, length=480, width=200))
    asm.join(ww.ThroughDovetail(tails=top.left_end, pins=side.right_end))
    return asm, side, top


def test_mortise_tenon_defaults_and_cut_sizes() -> None:
    asm, stile, rail = mortise_tenon()
    model = asm.resolve()

    joint = model.joints[0]
    assert isinstance(joint, ww.MortiseTenon)
    assert (joint.tenon_thickness, joint.tenon_length) == (8, pytest.approx(40))
    # The design is not changed by resolving.
    assert asm.joints[0].tenon_thickness is None

    assert model[stile].size == (600, 60, 20)
    assert model[rail].size == pytest.approx((340, 60, 20))


def test_mortise_tenon_geometry_matches_the_plain_example() -> None:
    asm, stile, rail = mortise_tenon()
    model = asm.resolve()
    stile_shape, rail_shape = model[stile].placed_shape, model[rail].placed_shape

    assert stile_shape.volume == pytest.approx(703200)
    assert rail_shape.volume == pytest.approx(376000)
    assert bbox(stile_shape) == (0, 0, 0, 60, 20, 600)
    assert bbox(rail_shape) == (20, 0, 270, 360, 20, 330)
    assert interference(stile_shape, rail_shape) == pytest.approx(0, abs=1e-6)


def test_dovetail_cut_sizes() -> None:
    asm, side, top = dovetail_corner()
    model = asm.resolve()
    assert model[side].size == (400, 200, 20)
    assert model[top].size == (500, 200, 20)


def test_dovetail_geometry_matches_the_plain_example() -> None:
    asm, side, top = dovetail_corner()
    model = asm.resolve()
    side_shape, top_shape = model[side].placed_shape, model[top].placed_shape

    assert side_shape.volume == pytest.approx(1542171.4286)
    assert top_shape.volume == pytest.approx(1977828.5714)
    assert bbox(side_shape) == (0, 0, 0, 20, 200, 400)
    assert bbox(top_shape) == (0, 0, 380, 500, 200, 400)
    assert interference(side_shape, top_shape) == pytest.approx(0, abs=1e-6)
    # Pins and tails fill the corner block: no gaps.
    blanks = 400 * 200 * 20 + 500 * 200 * 20 - 20 * 200 * 20
    assert side_shape.volume + top_shape.volume == pytest.approx(blanks)


def test_cut_list() -> None:
    asm, _, _ = mortise_tenon()
    assert asm.resolve().cut_list().splitlines() == [
        "stile  600 x 60 x 20 mm  oak",
        "       - mortise 50 x 8 mm, 42 deep, in stile.back_edge",
        "rail   340 x 60 x 20 mm  oak",
        "       - tenon 50 x 8 mm, 40 long, on rail.left_end",
    ]


def test_compound_has_all_parts_labelled() -> None:
    asm, _, _ = mortise_tenon()
    compound = asm.resolve().compound()
    assert compound.label == "mortise_tenon"
    assert [child.label for child in compound.children] == ["stile", "rail"]


def test_unconnected_part() -> None:
    asm, _, _ = mortise_tenon()
    asm.add(ww.Board("loose", OAK, length=100, width=50))
    with pytest.raises(ValueError, match="not connected to stile by joints: loose"):
        asm.resolve()


def test_joined_part_not_in_the_assembly() -> None:
    asm, stile, _ = mortise_tenon()
    other = ww.Board("other", OAK, length=100, width=50)
    asm.join(ww.MortiseTenon(tenon=other.left_end, mortise=stile.front_edge))
    with pytest.raises(ValueError, match="other is joined but not added"):
        asm.resolve()


def test_loop_that_does_not_close() -> None:
    asm, stile, rail = mortise_tenon()
    asm.join(ww.MortiseTenon(tenon=rail.left_end, mortise=stile.back_edge, position=ww.offset(100)))
    with pytest.raises(ValueError, match="doesn't close the loop"):
        asm.resolve()


def _volume(shape) -> float:
    """Volume of an intersection: nothing, one shape or a list of them."""
    if shape is None:
        return 0.0
    return sum(s.volume for s in shape) if isinstance(shape, list) else shape.volume


ROD = ww.Stock.rod(25, "oak")


def test_rod_resolves_to_a_cylinder_listed_by_its_diameter() -> None:
    asm = ww.Assembly("rail")
    rod = asm.add(ww.Rod("rung", ROD, length=380))
    model = asm.resolve()
    assert model[rod].shape.volume == pytest.approx(math.pi * 12.5**2 * 380)
    assert model[rod].size == (380, 25, 25)
    assert model.cut_list() == "rung  ø25 x 380 mm  oak"


def test_rod_butts_with_its_end() -> None:
    asm = ww.Assembly("peg_on_board")
    board = asm.add(ww.Board("board", OAK, length=300, width=100))
    peg = asm.add(ww.Rod("peg", ROD, length=80))
    asm.join(ww.Butt(board.top_face, peg.left_end, across=ww.centered()))
    model = asm.resolve()
    # Standing up from the middle of the board, its axis over the center.
    assert bbox(model[peg].placed_shape) == (137.5, 37.5, 0, 162.5, 62.5, 80)

    asm.joints[0] = ww.Butt(board.top_face, peg.bottom_face)
    with pytest.raises(ValueError, match="with its end, not with peg"):
        asm.resolve()


def test_joints_for_boards_refuse_rods() -> None:
    asm = ww.Assembly("dado")
    board = asm.add(ww.Board("board", OAK, length=300, width=100))
    rod = asm.add(ww.Rod("rung", ROD, length=200))
    asm.join(ww.DadoJoint(board.top_face, rod.left_end))
    with pytest.raises(ValueError, match="a DadoJoint joins boards, rung is a rod"):
        asm.resolve()


def test_rod_is_only_extended_at_its_ends() -> None:
    asm = ww.Assembly("rod")
    rod = asm.add(ww.Rod("rung", ROD, length=200))
    rod.cut(ww.ShapeCut(rod, bd.Box(1, 1, 1)))
    asm.resolve()
    rod.cuts[0].allowances = lambda: [ww.Allowance(rod.top_face, 5)]
    with pytest.raises(ValueError, match="only extended at its ends"):
        asm.resolve()
