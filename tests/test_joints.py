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
            total += _volume(overlap)
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


def test_through_dovetail_with_a_narrower_pin_board() -> None:
    asm = ww.Assembly("test")
    pins = asm.add(ww.Board("pins", OAK, length=300, width=80))
    tails = asm.add(ww.Board("tails", OAK, length=200, width=100))
    # The top edges flush, the pin board 20 mm above the bottom of the tail board.
    flush = (pins.back_edge, tails.back_edge)
    asm.join(
        ww.ThroughDovetail(tails=tails.left_end, pins=pins.right_end, tail_count=2, flush=flush)
    )
    model = asm.resolve()
    assert interference(model) == pytest.approx(0, abs=1e-6)
    total = model[pins].shape.volume + model[tails].shape.volume
    assert total == pytest.approx(320 * 80 * 20 + 200 * 100 * 20 + 20 * 20 * 20)
    with pytest.raises(ValueError, match="not be wider"):
        ww.ThroughDovetail(tails=pins.left_end, pins=tails.left_end)


def test_half_blind_dovetail() -> None:
    asm = ww.Assembly("test")
    front = asm.add(ww.Board("front", OAK, length=300, width=100))
    side = asm.add(ww.Board("side", ww.Stock.board(12, "oak"), length=200, width=100))
    asm.join(ww.HalfBlindDovetail(tails=side.left_end, pins=front.right_end, tail_count=2))
    model = asm.resolve()
    joint = model.joints[0]
    assert isinstance(joint, ww.HalfBlindDovetail)
    assert joint.lap == 5
    assert model[front].size == (312, 100, 20)
    assert model[side].size == (215, 100, 12)
    assert cuts(model, front) == ["sockets for 2 half-blind dovetails, 15 deep, lap 5"]
    assert cuts(model, side) == ["2 half-blind dovetails, 15 long, slope 1:7"]
    assert interference(model) == pytest.approx(0, abs=1e-6)
    # The tails fill the sockets: no gaps.
    total = model[front].shape.volume + model[side].shape.volume
    assert total == pytest.approx(312 * 100 * 20 + 200 * 100 * 12)
    # The lap stays whole: the outside face of the front is not cut.
    lap = bd.Pos(300, 0, -5) * bd.Box(12, 100, 5, align=(bd.Align.MIN,) * 3)
    assert (model[front].shape & lap).volume == pytest.approx(lap.volume)
    # The side's end lies inside the front, behind the lap.
    assert bbox(model[side].placed_shape) == (300, 0, -220, 312, 100, -5)
    with pytest.raises(ValueError, match="thinner than the pin board"):
        ww.HalfBlindDovetail(tails=side.left_end, pins=front.right_end, lap=20).reach()


def test_tongue_flush_with_the_reference_face() -> None:
    asm = ww.Assembly("test")
    rail = asm.add(ww.Board("rail", OAK, length=300, width=60))
    panel = asm.add(ww.Board("panel", ww.Stock.board(10, "oak"), length=300, width=200))
    asm.join(
        ww.TongueAndGroove(
            tongue=panel.front_edge,
            groove=rail.back_edge,
            tongue_thickness=6,
            tongue_length=8,
            tongue_offset=0,
            across=ww.centered(),
        )
    )
    model = asm.resolve()
    assert cuts(model, panel) == ["rabbet 8 mm, 4 deep, in panel.bottom_face at panel.front_edge"]
    assert cuts(model, rail)[0].startswith("groove 6 mm, 8 deep")
    assert interference(model) == pytest.approx(0, abs=1e-6)


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


@pytest.mark.parametrize("corner", [False, True])
def test_mitred_shoulder_tenon(corner: bool) -> None:
    stock = ww.Stock.board(30, "oak")
    asm = ww.Assembly("test")
    stile = asm.add(ww.Board("stile", stock, length=300, width=45))
    rail = asm.add(ww.Board("rail", stock, length=200, width=45))
    if corner:  # mitred at the inner edge only, the tenon through
        kw = dict(
            position=ww.flush_with(stile.right_end), mitred=(rail.back_edge,), tenon_length=30
        )
    else:
        kw = {}
    asm.join(ww.MitredShoulderTenon(tenon=rail.left_end, mortise=stile.back_edge, **kw))
    model = asm.resolve()
    joint = model.joints[0]
    # The mitres are a third of the stile deep; the tenon reaches half-way
    # under them, at a corner it keeps a full shoulder at the end of the stile.
    assert joint.mitre_depth == 15
    assert joint.shoulder == ((15, 7.5) if corner else (7.5, 7.5))
    mitres = 1 if corner else 2
    width, length = (22.5, 30) if corner else (30, 20)
    notch = (45 * 15 - mitres * 15 * 15 / 2) * 30
    # Under each mitre the tenon fills a triangle 7.5 x 7.5 mm, 10 thick.
    under = mitres * 7.5 * 7.5 / 2 * 10
    clearance = 0 if corner else width * 10 * 2
    assert model[rail].shape.volume == pytest.approx(
        200 * 45 * 30 + notch + under + width * 10 * length
    )
    assert model[rail].size[0] == 200 + 15 + length
    stile_volume = model[stile].shape.volume
    assert stile_volume == pytest.approx(
        300 * 45 * 30 - notch - under - width * 10 * length - clearance
    )
    assert cuts(model, stile) == (
        [
            "through mortise 22.5 x 10 mm in stile.back_edge",
            "notch 45 long, 15 deep, mitred at one end, in stile.back_edge",
        ]
        if corner
        else [
            "mortise 30 x 10 mm, 37 deep, in stile.back_edge",
            "notch 45 long, 15 deep, mitred at both ends, in stile.back_edge",
        ]
    )
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_mitred_shoulder_tenon_must_not_run_out_of_the_mitre() -> None:
    asm, stile, rail = stile_and_rail(rail_width=45)
    asm.join(ww.MitredShoulderTenon(tenon=rail.left_end, mortise=stile.back_edge, shoulder=0))
    with pytest.raises(ValueError, match="run out of the mitre"):
        asm.resolve()


def test_chamfered_tenon_standing_proud() -> None:
    asm, stile, rail = stile_and_rail()
    asm.join(
        ww.MortiseTenon(
            tenon=rail.left_end, mortise=stile.back_edge, tenon_length=50, tenon_chamfer=3
        )
    )
    model = asm.resolve()
    assert cuts(model, stile) == ["through mortise 30 x 8 mm in stile.back_edge"]
    assert cuts(model, rail) == ["tenon 30 x 8 mm, 50 long, end chamfered 3 mm, on rail.left_end"]
    # The tenon stands 10 mm proud of the stile's front edge (at y = 0).
    assert pytest.approx(-10) == model[rail].placed_shape.bounding_box().min.Y
    assert interference(model) == pytest.approx(0, abs=1e-6)


def _volume(shape) -> float:
    """Volume of an intersection: nothing, one shape or a list of them."""
    if shape is None:
        return 0.0
    return sum(s.volume for s in shape) if isinstance(shape, list) else shape.volume


def leg_with_two_aprons(tenon_length: float, mitred: bool) -> ww.Assembly:
    asm = ww.Assembly("test")
    leg = asm.add(ww.Board("leg", ww.Stock.board(45), length=700, width=45))
    for name, mortise, outside in [
        ("a", leg.back_edge, leg.bottom_face),
        ("b", leg.top_face, leg.front_edge),
    ]:
        apron = asm.add(ww.Board(name, OAK, length=300, width=100))
        asm.join(
            ww.MortiseTenon(
                tenon=apron.left_end,
                mortise=mortise,
                position=ww.flush_with(leg.right_end),
                flush=(outside, apron.ref_face),
                tenon_length=tenon_length,
                shoulder=10,
                mitre=apron.bottom_face if mitred else None,
            )
        )
    return asm


@pytest.mark.parametrize(
    ("tenon_length", "mitred", "clash"),
    [
        (31, False, False),  # short tenons pass each other
        (39, False, True),
        (39, True, False),  # mitred, their long points on the diagonal of the leg
        (40, True, True),
    ],
)
def test_two_tenons_meeting_in_a_leg(tenon_length: float, mitred: bool, clash: bool) -> None:
    model = leg_with_two_aprons(tenon_length, mitred).resolve()
    assert (interference(model) > 1e-6) == clash


def test_haunched_tenon_of_a_wide_apron() -> None:
    asm = ww.Assembly("test")
    leg = asm.add(ww.Board("leg", ww.Stock.board(45, "oak"), length=700, width=45))
    apron = asm.add(ww.Board("apron", OAK, length=400, width=150))
    asm.join(
        ww.MortiseTenon(
            tenon=apron.left_end,
            mortise=leg.back_edge,
            position=ww.flush_with(leg.right_end),
            shoulder=(40, 10),
            haunch=apron.front_edge,
            haunch_length=10,
        )
    )
    model = asm.resolve()
    # The apron's front edge is flush with the top of the leg; the haunch
    # fills the wide shoulder there, the mortise stops below the top.
    assert cuts(model, apron) == [
        "haunched tenon 100 x 8 mm, 30 long, haunch 10 long, on apron.left_end"
    ]
    assert cuts(model, leg) == [
        "mortise 100 x 8 mm, 32 deep, in leg.back_edge",
        "haunch mortise 40 x 8 mm, 10 deep, in leg.back_edge at leg.right_end",
    ]
    assert interference(model) == pytest.approx(0, abs=1e-6)


@pytest.mark.parametrize("play", [1.0, 5.0])
def test_button(play: float) -> None:
    asm = ww.Assembly("test")
    apron = asm.add(ww.Board("apron", OAK, length=600, width=120))
    button = asm.add(ww.Board("button", OAK, length=30, width=40))
    # The apron's reference face outside, its back edge up.
    asm.join(
        ww.Button(
            mortise=apron.bottom_face,
            tongue=button.right_end,
            level=apron.back_edge,
            position=ww.offset(100, ref=apron.left_end),
            play=play,
        )
    )
    model = asm.resolve()
    assert model[button].size == (36, 40, 20)
    assert cuts(model, button) == [
        "end rabbet 6 mm, 14 deep, in button.top_face at button.right_end"
    ]
    assert cuts(model, apron) == [f"mortise {40 + 2 * play:g} x 8 mm, 6 deep, in apron.bottom_face"]
    assert interference(model) == pytest.approx(0, abs=1e-6)
    # The button's top is level with the apron's, at 100 mm from its left end.
    box = model[button].placed_shape.bounding_box()
    assert pytest.approx(120) == box.max.Y
    assert pytest.approx((100, 140)) == (box.min.X, box.max.X)
    assert pytest.approx(-20 + 4) == box.max.Z  # the tongue reaches 4 mm into the apron
