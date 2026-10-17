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


def test_bridle_with_a_rail_as_thin_as_the_slot() -> None:
    asm = ww.Assembly("test")
    stile = asm.add(ww.Board("stile", ww.Stock.board(24), length=150, width=40))
    blade = asm.add(ww.Board("blade", ww.Stock.board(8), length=250, width=30))
    asm.join(
        ww.Bridle(
            tenon=blade.left_end,
            slot=stile.back_edge,
            position=ww.flush_with(stile.right_end),
            tenon_thickness=8,
            across=ww.centered(),
        )
    )
    model = asm.resolve()
    assert cuts(model, stile) == ["slot mortise 8 mm, 30 deep, in stile.right_end"]
    assert cuts(model, blade) == []  # it goes in whole
    assert model[blade].size == (290, 30, 8)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_mitre_corner_with_unequal_widths() -> None:
    asm = ww.Assembly("test")
    a = asm.add(ww.Board("a", OAK, length=300, width=40))
    b = asm.add(ww.Board("b", OAK, length=200, width=60))
    asm.join(ww.MitreCorner(a.right_end, b.left_end, a.back_edge, b.back_edge))
    model = asm.resolve()
    mitre_a, mitre_b = model[a].cuts[0], model[b].cuts[0]
    assert isinstance(mitre_a, ww.Mitre)
    assert isinstance(mitre_b, ww.Mitre)
    assert (mitre_a.shortening, mitre_b.shortening) == (pytest.approx(60), pytest.approx(40))
    # Outside lengths: the corner is at (300, 0) of part a.
    assert bbox(model[b].placed_shape) == (240, 0, -20, 300, 200, 0)
    assert interference(model) == pytest.approx(0, abs=1e-6)
    volume = 300 * 40 * 20 + 200 * 60 * 20 - 40 * 60 * 20  # the corner block is shared
    assert model[a].shape.volume + model[b].shape.volume == pytest.approx(volume)


def test_mitre_corner_needs_the_inside_sides() -> None:
    asm = ww.Assembly("test")
    a = asm.add(ww.Board("a", OAK, length=300, width=40))
    b = asm.add(ww.Board("b", OAK, length=200, width=40))
    asm.join(ww.MitreCorner(a.right_end, b.left_end, a.back_edge, b.front_edge))
    with pytest.raises(ValueError, match=r"b\.front_edge is not inside the corner"):
        asm.resolve()


@pytest.mark.parametrize(
    ("short", "b_short", "overlap"),
    [("back_edge", "front_edge", 40), ("bottom_face", "top_face", 20)],
)
def test_mitre_splice(short: str, b_short: str, overlap: float) -> None:
    asm = ww.Assembly("test")
    a = asm.add(ww.Board("a", OAK, length=300, width=40))
    b = asm.add(ww.Board("b", OAK, length=200, width=40))
    asm.join(ww.MitreSplice(a.right_end, b.left_end, short=getattr(a, short)))
    model = asm.resolve()
    assert cuts(model, b) == [f"mitre 45 deg on b.left_end, b.{b_short} inside"]
    assert bbox(model[b].placed_shape) == (300 - overlap, 0, -20, 500 - overlap, 40, 0)
    assert interference(model) == pytest.approx(0, abs=1e-6)
    volume = (300 + 200 - overlap) * 40 * 20
    assert model[a].shape.volume + model[b].shape.volume == pytest.approx(volume)


def test_cross_lap() -> None:
    asm = ww.Assembly("test")
    a = asm.add(ww.Board("a", OAK, length=300, width=40))
    b = asm.add(ww.Board("b", ww.Stock.board(30), length=200, width=50))
    asm.join(ww.CrossLap(a.back_edge, b.left_end, position=ww.offset(100, a.left_end), overhang=20))
    model = asm.resolve()
    assert cuts(model, a) == ["dado 50 mm, 10 deep, in a.top_face"]
    assert cuts(model, b) == ["dado 40 mm, 20 deep, in b.bottom_face"]
    # b crosses from the back edge of a, 20 mm beyond its front edge.
    assert bbox(model[b].placed_shape) == (100, -20, -30, 150, 180, 0)
    assert interference(model) == pytest.approx(0, abs=1e-6)


@pytest.mark.parametrize("half", [False, True])
def test_sliding_dovetail(half: bool) -> None:
    asm = ww.Assembly("test")
    side = asm.add(ww.Board("side", OAK, length=400, width=200))
    shelf = asm.add(ww.Board("shelf", OAK, length=300, width=200))
    asm.join(
        ww.SlidingDovetail(
            socket=side.bottom_face,
            end=shelf.left_end,
            position=ww.offset(150, side.right_end),
            half=half,
        )
    )
    model = asm.resolve()
    joint = model.joints[0]
    assert (joint.depth, joint.thickness) == (6.5, 10)
    assert cuts(model, side) == [
        "dovetail socket 10 mm at the face, 6.5 deep, 1:7, in side.bottom_face"
    ]
    assert model[shelf].size == (306.5, 200, 20)
    assert interference(model) == pytest.approx(0, abs=1e-6)
    # The tongue fills the socket exactly.
    total = model[side].shape.volume + model[shelf].shape.volume
    assert total == pytest.approx((400 + 300) * 200 * 20)


def test_interlocking_rabbets() -> None:
    asm, side, top = stile_and_rail()
    asm.join(ww.RabbetJoint(rabbet=side.bottom_face, end=top.left_end, at=side.right_end, lap=10))
    model = asm.resolve()
    assert cuts(model, side) == [
        "end rabbet 10 mm, 10 deep, in stile.bottom_face at stile.right_end"
    ]
    assert cuts(model, top) == ["lap 10 mm thick, 10 long, on rail.left_end"]
    assert interference(model) == pytest.approx(0, abs=1e-6)
    total = model[side].shape.volume + model[top].shape.volume
    assert total == pytest.approx((300 + 200) * 40 * 20)


@pytest.mark.parametrize("pins_end", ["left_end", "right_end"])
@pytest.mark.parametrize("tails_end", ["left_end", "right_end"])
def test_through_dovetail_on_any_ends(pins_end: str, tails_end: str) -> None:
    asm = ww.Assembly("test")
    pins = asm.add(ww.Board("pins", OAK, length=300, width=100))
    tails = asm.add(ww.Board("tails", OAK, length=200, width=100))
    asm.join(
        ww.ThroughDovetail(
            tails=getattr(tails, tails_end), pins=getattr(pins, pins_end), tail_count=2
        )
    )
    model = asm.resolve()
    assert interference(model) == pytest.approx(0, abs=1e-6)
    # Pins and tails fill the corner block: no gaps.
    total = model[pins].shape.volume + model[tails].shape.volume
    assert total == pytest.approx((320 + 220 - 20) * 100 * 20)
    # The tail board stands beyond the pin board's end, against its inside face.
    x0 = -20 if pins_end == "left_end" else 300
    assert bbox(model[tails].placed_shape) == (x0, 0, -220, x0 + 20, 100, 0)


def test_through_dovetail_only_on_ends() -> None:
    _, stile, rail = stile_and_rail()
    with pytest.raises(ValueError, match="on the ends"):
        ww.ThroughDovetail(tails=rail.left_end, pins=stile.back_edge)


def test_drawer_with_pins_and_tails_on_both_ends() -> None:
    from woodwright.examples import projects

    model = projects.dovetail_drawer().resolve()
    assert interference(model) == pytest.approx(0, abs=1e-6)
    for name, kind in [
        ("front", "sockets"),
        ("back", "sockets"),
        ("left", "3 dovetails"),
        ("right", "3 dovetails"),
    ]:
        part = next(p for p in model.parts if p.part.name == name)
        assert [cut.describe().startswith(kind) for cut in part.cuts] == [True, True]


def test_haunched_mortise_and_tenon() -> None:
    asm = ww.Assembly("test")
    stile = asm.add(ww.Board("stile", OAK, length=300, width=60))
    rail = asm.add(ww.Board("rail", OAK, length=200, width=60))
    asm.join(
        ww.MortiseTenon(
            tenon=rail.left_end,
            mortise=stile.back_edge,
            position=ww.flush_with(stile.right_end),
            shoulder=10,
            haunch=rail.front_edge,
        )
    )
    model = asm.resolve()
    assert model.joints[0].haunch_length == 10  # as deep as a panel groove
    assert cuts(model, stile) == [
        "mortise 40 x 8 mm, 42 deep, in stile.back_edge",
        "haunch mortise 10 x 8 mm, 10 deep, in stile.back_edge at stile.right_end",
    ]
    assert cuts(model, rail) == [
        "haunched tenon 40 x 8 mm, 40 long, haunch 10 long, on rail.left_end"
    ]
    assert interference(model) == pytest.approx(0, abs=1e-6)
