"""Joints: placement, allowances and the cuts derived for both parts."""

import build123d as bd
import pytest

import woodwright as ww

OAK = ww.Stock.board(20, "oak")


def interference(model: ww.ResolvedModel) -> float:
    shapes = [part.placed_shape for part in model.parts]
    total = 0.0
    for i, a in enumerate(shapes):
        for b in shapes[i + 1 :]:
            overlap = a.intersect(b)
            total += overlap.volume if overlap is not None else 0.0
    return total


def cuts(model: ww.ResolvedModel, part: ww.Board) -> list[str]:
    return [cut.describe() for cut in model[part].cuts]


def bbox(shape: bd.Shape) -> tuple:
    box = shape.bounding_box()
    return pytest.approx((*box.min, *box.max), abs=1e-6)


def stile_and_rail(rail_width: float = 40) -> tuple[ww.Assembly, ww.Board, ww.Board]:
    asm = ww.Assembly("test")
    stile = asm.add(ww.Board("stile", OAK, length=300, width=40))
    rail = asm.add(ww.Board("rail", OAK, length=200, width=rail_width))
    return asm, stile, rail


def test_butt_edge_to_edge() -> None:
    asm, a, b = stile_and_rail()
    asm.join(ww.Butt(a.back_edge, b.front_edge, position=ww.flush_with(a.left_end)))
    model = asm.resolve()
    assert bbox(model[b].placed_shape) == (0, 40, -20, 200, 80, 0)
    assert cuts(model, a) == cuts(model, b) == []


def test_dado_joint() -> None:
    asm, side, shelf = stile_and_rail()
    asm.join(
        ww.DadoJoint(dado=side.top_face, end=shelf.left_end, position=ww.offset(100, side.left_end))
    )
    model = asm.resolve()
    assert model.joints[0].depth == 6.5  # a third of 20, rounded to 0.5 mm
    assert model[shelf].size == (206.5, 40, 20)
    assert cuts(model, side) == ["dado 20 mm, 6.5 deep, in stile.top_face"]
    assert bbox(model[shelf].placed_shape) == (100, 0, -6.5, 120, 40, 200)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_rabbet_joint() -> None:
    asm, side, top = stile_and_rail()
    asm.join(ww.RabbetJoint(rabbet=side.bottom_face, end=top.left_end, at=side.right_end))
    model = asm.resolve()
    assert cuts(model, side) == [
        "end rabbet 20 mm, 10 deep, in stile.bottom_face at stile.right_end"
    ]
    assert model[top].size == (210, 40, 20)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_groove_joint_through_or_stopped() -> None:
    for through, expected in [
        (True, "groove 10 mm, 10 deep, in stile.back_edge"),
        (False, "mortise 200 x 10 mm, 10 deep, in stile.back_edge"),
    ]:
        asm = ww.Assembly("test")
        stile = asm.add(ww.Board("stile", OAK, length=300, width=40))
        panel = asm.add(ww.Board("panel", ww.Stock.board(10), length=200, width=100))
        asm.join(ww.GrooveJoint(groove=stile.back_edge, edge=panel.front_edge, through=through))
        model = asm.resolve()
        assert cuts(model, stile) == [expected]
        # The panel is centered across the stile's thickness.
        assert bbox(model[panel].placed_shape) == (50, 30, -15, 250, 140, -5)


def test_tongue_and_groove() -> None:
    asm, a, b = stile_and_rail()
    asm.join(ww.TongueAndGroove(tongue=b.front_edge, groove=a.back_edge))
    model = asm.resolve()
    assert cuts(model, a) == ["groove 8 mm, 10 deep, in stile.back_edge"]
    assert cuts(model, b) == ["tongue 8 mm thick, 10 long, on rail.front_edge"]
    assert model[b].size == (200, 50, 20)
    assert interference(model) == pytest.approx(0, abs=1e-6)


@pytest.mark.parametrize(
    ("position", "socket"),
    [
        (ww.flush_with, "end rabbet 40 mm, 10 deep, in stile.bottom_face at stile.right_end"),
        (lambda end: ww.centered(), "dado 40 mm, 10 deep, in stile.bottom_face"),
    ],
)
def test_half_lap(position, socket: str) -> None:
    asm, stile, rail = stile_and_rail()
    asm.join(
        ww.HalfLap(lap=rail.left_end, socket=stile.back_edge, position=position(stile.right_end))
    )
    model = asm.resolve()
    assert cuts(model, stile) == [socket]
    assert cuts(model, rail) == ["lap 10 mm thick, 40 long, on rail.left_end"]
    assert model[stile].shape.volume + model[rail].shape.volume == pytest.approx(
        (300 + 200) * 40 * 20
    )
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_half_lap_over() -> None:
    asm, stile, rail = stile_and_rail()
    asm.join(ww.HalfLap(lap=rail.left_end, socket=stile.back_edge, over=True))
    model = asm.resolve()
    assert cuts(model, stile) == ["dado 40 mm, 10 deep, in stile.top_face"]


def test_bridle_with_a_narrow_rail() -> None:
    asm, stile, rail = stile_and_rail(rail_width=25)
    asm.join(
        ww.Bridle(
            tenon=rail.left_end, slot=stile.back_edge, position=ww.flush_with(stile.right_end)
        )
    )
    model = asm.resolve()
    assert cuts(model, stile) == ["slot mortise 8 mm, 25 deep, in stile.right_end"]
    assert cuts(model, rail) == ["tenon 8 mm thick, 40 long, on rail.left_end"]
    assert model[rail].size == (240, 25, 20)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_mortise_tenon_with_offset_tenon() -> None:
    asm, stile, rail = stile_and_rail()
    asm.join(ww.MortiseTenon(tenon=rail.left_end, mortise=stile.back_edge, tenon_offset=4))
    model = asm.resolve()
    tenon = model[rail].cuts[0]
    assert isinstance(tenon, ww.Tenon)
    assert tenon.tenon_box()[2] == (-12, -4)
    mortise = model[stile].cuts[0]
    assert mortise.ranges()[2] == pytest.approx((-12, -4))
