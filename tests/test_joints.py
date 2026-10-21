"""Joints: placement, allowances and the cuts derived for both parts."""

import math
from dataclasses import replace

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


def test_stopped_dado_joint_notches_the_shelf() -> None:
    asm = ww.Assembly("test")
    side = asm.add(ww.Board("side", OAK, length=400, width=200))
    shelf = asm.add(ww.Board("shelf", OAK, length=300, width=200))
    asm.join(
        ww.DadoJoint(
            dado=side.bottom_face,
            end=shelf.left_end,
            position=ww.offset(150, side.right_end),
            stopped={side.front_edge: 15},
        )
    )
    model = asm.resolve()
    assert cuts(model, side) == [
        "stopped dado 20 mm, 6.5 deep, in side.bottom_face, 15 mm short of side.front_edge"
    ]
    assert cuts(model, shelf) == ["notch 15 x 6.5 mm in shelf.left_end at shelf.front_edge"]
    assert model[side].shape.volume == pytest.approx(400 * 200 * 20 - 20 * 185 * 6.5)
    assert model[shelf].shape.volume == pytest.approx(306.5 * 200 * 20 - 15 * 6.5 * 20)
    # The shelf's front edge stays flush with the side's.
    assert bbox(model[shelf].placed_shape) == (230, 0, -320, 250, 200, -13.5)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_stopped_tongue_and_groove_cuts_back_the_tongue() -> None:
    asm, a, b = stile_and_rail()
    asm.join(
        ww.TongueAndGroove(
            tongue=b.front_edge,
            groove=a.back_edge,
            position=ww.flush_with(a.left_end),
            stopped={a.left_end: 20},
        )
    )
    model = asm.resolve()
    assert cuts(model, a) == [
        "stopped groove 8 mm, 10 deep, in stile.back_edge, 20 mm short of stile.left_end"
    ]
    assert cuts(model, b) == [
        "tongue 8 mm thick, 10 long, on rail.front_edge",
        "notch 20 x 10 mm in rail.front_edge at rail.left_end",
    ]
    assert model[b].shape.volume == pytest.approx(200 * 40 * 20 + 180 * 10 * 8)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_a_stop_away_from_the_inserted_part_leaves_it_whole() -> None:
    asm, a, b = stile_and_rail()
    asm.join(ww.TongueAndGroove(tongue=b.front_edge, groove=a.back_edge, stopped={a.left_end: 20}))
    model = asm.resolve()
    assert cuts(model, b) == ["tongue 8 mm thick, 10 long, on rail.front_edge"]
    with pytest.raises(ValueError, match="next to it"):
        asm = ww.Assembly("test")
        a, b = asm.add(a), asm.add(b)
        asm.join(ww.DadoJoint(dado=a.top_face, end=b.left_end, stopped={a.bottom_face: 5}))
        asm.resolve()


def test_stopped_rabbet_joint() -> None:
    asm, side, top = stile_and_rail()
    asm.join(
        ww.RabbetJoint(
            rabbet=side.bottom_face,
            end=top.left_end,
            at=side.right_end,
            stopped={side.front_edge: 10},
        )
    )
    model = asm.resolve()
    assert cuts(model, side) == [
        "stopped end rabbet 20 mm, 10 deep, in stile.bottom_face at stile.right_end, "
        "10 mm short of stile.front_edge"
    ]
    assert cuts(model, top) == ["notch 10 x 10 mm in rail.left_end at rail.front_edge"]
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


def test_bevelled_edge_in_a_groove_without_a_tongue() -> None:
    # Like a raised panel: bevelled on both faces down to the groove's width
    # at its mouth and on into it, going in whole.
    asm, a, b = stile_and_rail()
    asm.join(ww.TongueAndGroove(tongue=b.front_edge, groove=a.back_edge, cut_tongue=False))
    for face in (b.bottom_face, b.top_face):
        b.cut(ww.Chamfer(b.arris(face, b.front_edge), size=30, size_b=6, run_out=True))
    model = asm.resolve()
    assert cuts(model, a) == ["groove 8 mm, 10 deep, in stile.back_edge"]
    assert cuts(model, b)[0] == (
        "chamfer 30 x 6 mm on rail.bottom_face_front_edge_arris, running out past rail.front_edge"
    )
    assert model[b].size == (200, 50, 20)
    # 8 mm thick at the mouth of the groove, 4 mm at the edge, 10 mm further.
    bevels = 2 * 30 * 6 / 2 * 200
    assert model[b].shape.volume == pytest.approx(200 * 40 * 20 - bevels + 200 * 10 * 6)
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


@pytest.mark.parametrize("corner", [False, True])
def test_dovetail_half_lap(corner: bool) -> None:
    asm, stile, rail = stile_and_rail()
    kw = dict(position=ww.flush_with(stile.right_end)) if corner else {}
    asm.join(ww.DovetailHalfLap(lap=rail.left_end, socket=stile.back_edge, **kw))
    model = asm.resolve()
    # At a corner only the inner edge slopes, 40 / 7 mm over the lap.
    joint = model.joints[0]
    assert joint.sloped == ((rail.back_edge,) if corner else (rail.front_edge, rail.back_edge))
    shoulder = 40 - (1 if corner else 2) * 40 / 7
    kind = "half-dovetail lap" if corner else "dovetail lap"
    assert cuts(model, stile) == [
        f"dovetail socket {round(shoulder, 1):g} to 40 mm, 10 deep, 1:7, in stile.bottom_face"
    ]
    assert cuts(model, rail) == [
        f"{kind} 10 mm thick, 40 long, {round(shoulder, 1):g} wide at the shoulder, 1:7, "
        "on rail.left_end"
    ]
    assert model[rail].size == (240, 40, 20)
    # The tail fills the socket exactly.
    tail = (shoulder + 40) / 2 * 40 * 10
    assert model[stile].shape.volume == pytest.approx(300 * 40 * 20 - tail)
    assert model[rail].shape.volume == pytest.approx(200 * 40 * 20 + tail)
    x0 = 260 if corner else 130
    assert bbox(model[rail].placed_shape) == (x0, 0, -20, x0 + 40, 240, 0)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_half_lap_standing_proud_lets_in_an_uncut_rail() -> None:
    asm, stile, rail = stile_and_rail()
    asm.join(
        ww.HalfLap(lap=rail.left_end, socket=stile.back_edge, lap_thickness=20, over=True, proud=10)
    )
    model = asm.resolve()
    assert cuts(model, stile) == ["dado 40 mm, 10 deep, in stile.top_face"]
    assert cuts(model, rail) == []
    # Let in half its thickness, the other half standing out of the stile's top face.
    assert bbox(model[rail].placed_shape) == (130, 0, -10, 170, 240, 10)
    assert model[stile].shape.volume == pytest.approx(300 * 40 * 20 - 40 * 40 * 10)
    assert interference(model) == pytest.approx(0, abs=1e-6)


@pytest.mark.parametrize(
    ("kw", "message"),
    [
        (dict(proud=10), "still reach into"),  # a 10 mm lap standing 10 mm proud
        (dict(proud=5, flush=None), "beyond a face"),
    ],
)
def test_half_lap_standing_proud_must_reach_in(kw: dict, message: str) -> None:
    asm, stile, rail = stile_and_rail()
    if "flush" in kw:
        kw["flush"] = (stile.right_end, rail.front_edge)
    asm.join(ww.HalfLap(lap=rail.left_end, socket=stile.back_edge, **kw))
    with pytest.raises(ValueError, match=message):
        asm.resolve()


def test_dovetail_half_lap_standing_proud() -> None:
    asm, stile, rail = stile_and_rail()
    asm.join(
        ww.DovetailHalfLap(
            lap=rail.left_end,
            socket=stile.back_edge,
            position=ww.flush_with(stile.right_end),
            over=True,
            proud=5,
            slope=4,
            sloped=(rail.front_edge,),
        )
    )
    model = asm.resolve()
    assert cuts(model, stile) == ["dovetail socket 30 to 40 mm, 5 deep, 1:4, in stile.top_face"]
    assert cuts(model, rail) == [
        "half-dovetail lap 10 mm thick, 40 long, 30 wide at the shoulder, 1:4, on rail.left_end"
    ]
    # The rail stands 5 mm out of the stile's top face.
    assert bbox(model[rail].placed_shape) == (260, 0, -15, 300, 240, 5)
    # The triangle beside the tail, 40 long and 10 across at the shoulder,
    # through the lap, but only 5 deep in the socket.
    triangle = 40 * 10 / 2
    assert model[rail].shape.volume == pytest.approx(240 * 40 * 20 - 40 * 40 * 10 - triangle * 10)
    assert model[stile].shape.volume == pytest.approx(300 * 40 * 20 - (40 * 40 - triangle) * 5)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_dovetail_half_lap_stopped_short_of_the_end() -> None:
    asm, stile, rail = stile_and_rail()
    asm.join(
        ww.DovetailHalfLap(
            lap=rail.left_end,
            socket=stile.back_edge,
            position=ww.flush_with(stile.right_end),
            stopped={stile.right_end: 10},
            sloped=(rail.front_edge,),
        )
    )
    model = asm.resolve()
    # The tail is 30 wide at its end, sloping in from there by 40 / 7.
    shoulder = 30 - 40 / 7
    assert cuts(model, stile) == [
        f"dovetail socket {round(shoulder, 1):g} to 30 mm, 10 deep, 1:7, in stile.bottom_face, "
        "10 mm short of stile.right_end"
    ]
    assert cuts(model, rail) == [
        f"half-dovetail lap 10 mm thick, 40 long, {round(shoulder, 1):g} wide at the shoulder, "
        "1:7, cut back 10 at rail.front_edge, on rail.left_end"
    ]
    tail = (30 + shoulder) / 2 * 40 * 10
    assert model[stile].shape.volume == pytest.approx(300 * 40 * 20 - tail)
    assert model[rail].shape.volume == pytest.approx(200 * 40 * 20 + tail)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_dovetail_lap_too_long_for_its_slope() -> None:
    asm, stile, rail = stile_and_rail()
    asm.join(ww.DovetailHalfLap(lap=rail.left_end, socket=stile.back_edge, slope=1))
    with pytest.raises(ValueError, match="too long for its slope"):
        asm.resolve()


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


KEY = ww.Stock.board(3, "walnut")


def keyed_frame_corner(**kwargs) -> tuple[ww.ResolvedModel, ww.Board, ww.Board, ww.Board]:
    asm = ww.Assembly("test")
    a = asm.add(ww.Board("a", OAK, length=300, width=40))
    b = asm.add(ww.Board("b", OAK, length=200, width=40))
    key = asm.add(ww.Board("key", kwargs.pop("stock", KEY), length=50, width=20))
    asm.join(
        ww.KeyedMitre(a.right_end, b.left_end, a.back_edge, b.back_edge, keys=(key,), **kwargs)
    )
    return asm.resolve(), a, b, key


def test_keyed_mitre() -> None:
    model, a, b, key = keyed_frame_corner()
    # A third of the mitre line (40 * sqrt(2)), in the middle of the thickness.
    assert cuts(model, a) == [
        "mitre 45 deg on a.right_end, a.back_edge inside",
        "key kerf 3 mm wide, 19 deep across the corner with b, 10 from a.top_face",
    ]
    assert cuts(model, b)[1] == (
        "key kerf 3 mm wide, 19 deep across the corner with a, 10 from b.top_face"
    )
    assert cuts(model, key) == ["trimmed flush with a and b, to a triangle"]
    # Trimmed to a right triangle with legs of 19 * sqrt(2) along the outside edges.
    leg = 19 * math.sqrt(2)
    assert bbox(model[key].placed_shape) == (300 - leg, 0, -11.5, 300, leg, -8.5)
    assert model[key].shape.volume == pytest.approx(19 * 19 * 3)
    assert model[a].shape.volume == pytest.approx(300 * 40 * 20 - 40 * 40 * 10 - 19 * 19 * 1.5)
    assert interference(model) == pytest.approx(0, abs=1e-6)


@pytest.mark.parametrize(
    ("kwargs", "volume"),
    [
        ({"angle": 15.0}, 19 * 19 * 3 / math.cos(math.radians(15))),
        ({"depth": 14.0, "dovetail": 8.0, "stock": ww.Stock.board(10, "walnut")}, None),
    ],
)
def test_keyed_mitre_variants(kwargs: dict, volume: float | None) -> None:
    model, *_, key = keyed_frame_corner(**kwargs)
    if volume is None:  # a dovetail 10 mm wide at its bottom, 14 deep
        top = 10 - 2 * 14 * math.tan(math.radians(8))
        volume = 14 * 14 * (2 * 10 + top) / 3  # a triangle, thinner towards its apex
    assert model[key].shape.volume == pytest.approx(volume, rel=1e-6)
    assert interference(model) == pytest.approx(0, abs=1e-6)
    total = 300 * 40 * 20 + 200 * 40 * 20 - 40 * 40 * 20
    assert sum(part.shape.volume for part in model.parts) == pytest.approx(total)


def test_keyed_box_corner_with_keys_of_varying_depths() -> None:
    asm = ww.Assembly("test")
    a = asm.add(ww.Board("a", OAK, length=300, width=120))
    b = asm.add(ww.Board("b", OAK, length=200, width=120))
    keys = tuple(asm.add(ww.Board(f"key_{i}", KEY, length=30, width=12)) for i in range(3))
    joint = ww.KeyedMitre(
        a.right_end, b.left_end, a.bottom_face, b.bottom_face, keys=keys, depth=(6.0, 9.0, 6.0)
    )
    asm.join(joint)
    model = asm.resolve()
    for cut, depth, y in zip(cuts(model, a)[1:], (6, 9, 6), (30, 60, 90), strict=True):
        assert cut.endswith(f"{depth} deep across the corner with b, {y} from a.front_edge")
    for key, depth, y in zip(keys, (6, 9, 6), (30, 60, 90), strict=True):
        leg = depth * math.sqrt(2)
        assert bbox(model[key].placed_shape) == (300 - leg, y - 1.5, -leg, 300, y + 1.5, 0)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_keyed_mitre_checks_its_keys() -> None:
    with pytest.raises(ValueError, match="too small to fill its kerf"):
        keyed_frame_corner(depth=25.0)
    with pytest.raises(ValueError, match="closes before the corner"):
        keyed_frame_corner(dovetail=10.0)
    asm = ww.Assembly("test")
    a = asm.add(ww.Board("a", OAK, length=300, width=40))
    b = asm.add(ww.Board("b", OAK, length=200, width=40))
    key = ww.Board("key", KEY, length=50, width=20)
    with pytest.raises(ValueError, match="one depth for each key"):
        ww.KeyedMitre(
            a.right_end, b.left_end, a.back_edge, b.back_edge, keys=(key,), depth=(5.0, 6.0)
        )
    joint = ww.KeyedMitre(
        a.right_end, b.left_end, a.back_edge, b.back_edge, keys=(key,), depth=60.0
    )
    with pytest.raises(ValueError, match="short of the inside corner"):
        joint.with_defaults()


SPLINE = ww.Stock.board(4, "plywood")


def box_corner(width: float) -> tuple[ww.Assembly, ww.Board, ww.Board]:
    asm = ww.Assembly("test")
    a = asm.add(ww.Board("a", OAK, length=300, width=width))
    b = asm.add(ww.Board("b", OAK, length=200, width=width))
    return asm, a, b


def test_splined_mitre_through_a_box_corner() -> None:
    asm, a, b = box_corner(120)
    spline = asm.add(ww.Board("spline", SPLINE, length=120, width=16))
    asm.join(
        ww.SplinedMitre(a.right_end, b.left_end, a.bottom_face, b.bottom_face, splines=(spline,))
    )
    model = asm.resolve()
    assert cuts(model, a)[1] == (
        "spline groove 4 mm, 9 deep, square to the mitre with b, along the corner, through"
    )
    # In the middle of the mitre line, square to it: half of 16 mm into each part.
    r = (8 + 2) / math.sqrt(2)  # from the middle of the mitre to the spline's corners
    mid = 10
    assert bbox(model[spline].placed_shape) == (
        300 - mid - r,
        0,
        -mid - r,
        300 - mid + r,
        120,
        -mid + r,
    )
    removed = 20 * 20 * 120 / 2 + 120 * 4 * 9
    assert model[a].shape.volume == pytest.approx(300 * 120 * 20 - removed)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_splined_mitre_in_a_row_along_a_wide_corner() -> None:
    asm, a, b = box_corner(250)
    splines = tuple(asm.add(ww.Board(f"s{i}", SPLINE, length=50, width=16)) for i in range(3))
    asm.join(
        ww.SplinedMitre(a.right_end, b.left_end, a.bottom_face, b.bottom_face, splines=splines)
    )
    model = asm.resolve()
    # Equal gaps: 25 mm between the splines and at the edges.
    assert [cut.split(", stopped, ")[1] for cut in cuts(model, b)[1:]] == [
        f"{start} to {start + 50} from b.front_edge" for start in (25, 100, 175)
    ]
    for s, y in zip(splines, (25, 100, 175), strict=True):
        box = model[s].placed_shape.bounding_box()
        low, high = box.min.Y, box.max.Y
        assert (low, high) == pytest.approx((y, y + 50))
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_splined_mitre_along_the_mitre_line() -> None:
    asm = ww.Assembly("test")
    a = asm.add(ww.Board("a", OAK, length=300, width=40))
    b = asm.add(ww.Board("b", OAK, length=200, width=40))
    spline = asm.add(ww.Board("spline", SPLINE, length=40, width=12))
    joint = ww.SplinedMitre(
        a.right_end, b.left_end, a.back_edge, b.back_edge, splines=(spline,), along="mitre"
    )
    asm.join(joint)
    model = asm.resolve()
    assert cuts(model, a)[1] == (
        "spline groove 4 mm, 7 deep, square to the mitre with b, along the mitre line, "
        "10 from a.top_face"
    )
    box = model[spline].placed_shape.bounding_box()
    low, high = box.min.Z, box.max.Z
    assert (low, high) == pytest.approx((-12, -8))
    assert interference(model) == pytest.approx(0, abs=1e-6)
    # Reaching the inside corner, the groove runs out there.
    joint = replace(joint, spline_offset=40 * math.sqrt(2) - 20)
    assert (
        ", out at the inside corner, "
        in joint.with_defaults().cuts(joint.placement())[2].describe()
    )
    # Towards the outside corner, it would break out of the outside edges.
    joint = replace(joint, spline_offset=20)
    with pytest.raises(ValueError, match="breaks out of"):
        joint.with_defaults().cuts(joint.placement())


@pytest.mark.parametrize("face", ["top_face", "bottom_face"])
def test_mitred_half_lap(face: str) -> None:
    asm = ww.Assembly("test")
    a = asm.add(ww.Board("a", OAK, length=300, width=40))
    b = asm.add(ww.Board("b", OAK, length=200, width=40))
    joint = ww.MitredHalfLap(
        a.right_end, b.left_end, a.back_edge, b.back_edge, face=getattr(a, face)
    )
    asm.join(joint)
    model = asm.resolve()
    back = "bottom_face" if face == "top_face" else "top_face"
    assert cuts(model, a) == [
        f"mitre 45 deg on a.right_end, a.back_edge inside, 10 deep from a.{face}"
    ]
    assert cuts(model, b) == [
        f"mitre 45 deg on b.left_end, b.back_edge inside, 10 deep from b.{face}",
        f"end rabbet 40 mm, 10 deep, in b.{back} at b.left_end",
    ]
    # Outside lengths, as for a mitre corner.
    assert bbox(model[b].placed_shape) == (260, 0, -20, 300, 200, 0)
    assert interference(model) == pytest.approx(0, abs=1e-6)
    # Part a keeps the lap behind the mitre, part b only its half of the mitre.
    triangle = 40 * 40 / 2 * 10
    assert model[a].shape.volume == pytest.approx(300 * 40 * 20 - triangle)
    assert model[b].shape.volume == pytest.approx(200 * 40 * 20 - triangle - 40 * 40 * 10)


@pytest.mark.parametrize("face", ["top_face", "bottom_face"])
def test_mitred_face_tenon(face: str) -> None:
    stock = ww.Stock.board(30, "oak")
    asm = ww.Assembly("test")
    a = asm.add(ww.Board("a", stock, length=300, width=48))
    b = asm.add(ww.Board("b", stock, length=200, width=48))
    joint = ww.MitredFaceTenon(
        a.right_end, b.left_end, a.back_edge, b.back_edge, face=getattr(a, face), clearance=0
    )
    asm.join(joint)
    model = asm.resolve()
    back = "bottom_face" if face == "top_face" else "top_face"
    assert cuts(model, a) == [
        f"mitre 45 deg on a.right_end, a.back_edge inside, 10 deep from a.{face}",
        "mortise 24 x 8 mm, 32 deep, in a.back_edge",
    ]
    assert cuts(model, b) == [
        f"mitre 45 deg on b.left_end, b.back_edge inside, 10 deep from b.{face}",
        f"end rabbet 48 mm, 20 deep, in b.{back} at b.left_end, leaving a tenon 24 x 8 mm, 32 long",
    ]
    # The tenon: a quarter of the width in from both edges, centered in the
    # layer behind the mitre (6 mm cheeks), 32 mm into part a from its inside edge.
    z = (-24, -16) if face == "top_face" else (-14, -6)
    behind = bd.Box(48, 48, 20, align=(bd.Align.MIN,) * 3).moved(
        bd.Location((252, 0, -30 if face == "top_face" else -20))
    )
    assert bbox(behind & model[b].placed_shape) == (264, 16, z[0], 288, 48, z[1])
    assert interference(model) == pytest.approx(0, abs=1e-6)
    # Without clearance the parts fill their design boxes, less the corner they share.
    triangle = 48 * 48 / 2 * 10
    tenon_volume = 32 * 24 * 8
    assert model[a].shape.volume == pytest.approx(300 * 48 * 30 - triangle - tenon_volume)
    rabbet = 48 * 48 * 20
    assert model[b].shape.volume == pytest.approx(200 * 48 * 30 - triangle - rabbet + tenon_volume)
    total = model[a].shape.volume + model[b].shape.volume
    assert total == pytest.approx((300 + 200 - 48) * 48 * 30)


def test_mitred_face_tenon_has_shoulders_behind_the_mitre() -> None:
    _, a, b = stile_and_rail()
    with pytest.raises(ValueError, match="shoulders at both edges"):
        ww.MitredFaceTenon(
            a.right_end, b.left_end, a.back_edge, b.back_edge, shoulder=(0, 10)
        ).with_defaults()
    with pytest.raises(ValueError, match="behind the mitre"):
        ww.MitredFaceTenon(
            a.right_end, b.left_end, a.back_edge, b.back_edge, tenon_offset=2
        ).with_defaults()


def test_mitre_corner_along_the_edges() -> None:
    asm = ww.Assembly("test")
    a = asm.add(ww.Board("a", OAK, length=300, width=60))
    b = asm.add(ww.Board("b", OAK, length=300, width=40))
    asm.join(ww.MitreCorner(a.back_edge, b.front_edge, a.bottom_face, b.bottom_face))
    model = asm.resolve()
    assert cuts(model, a) == ["mitre 45 deg on a.back_edge, a.bottom_face inside"]
    assert cuts(model, b) == ["mitre 45 deg on b.front_edge, b.bottom_face inside"]
    # A long L: outside widths, the left ends flush, b below a's back edge.
    assert bbox(model[b].placed_shape) == (0, 40, -40, 300, 60, 0)
    assert interference(model) == pytest.approx(0, abs=1e-6)
    volume = 300 * (60 * 20 + 40 * 20 - 20 * 20)  # the corner block is shared
    assert model[a].shape.volume + model[b].shape.volume == pytest.approx(volume)
    with pytest.raises(ValueError, match="two ends or two edges"):
        ww.MitreCorner(a.right_end, b.front_edge, a.bottom_face, b.bottom_face).placement()


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


@pytest.mark.parametrize(
    ("kw", "fingers", "described"),
    [
        ({}, 5, ("3 fingers 20 mm wide", "2 fingers 20 mm wide")),
        ({"finger_width": 12}, 9, ("5 fingers 11.1 mm wide", "4 fingers 11.1 mm wide")),
        ({"fingers": 4}, 4, ("2 fingers 25 mm wide", "2 fingers 25 mm wide")),
    ],
)
def test_box_joint(kw: dict, fingers: int, described: tuple[str, str]) -> None:
    asm = ww.Assembly("test")
    a = asm.add(ww.Board("a", OAK, length=300, width=100))
    b = asm.add(ww.Board("b", ww.Stock.board(12, "oak"), length=200, width=100))
    asm.join(ww.BoxJoint(a.right_end, b.left_end, **kw))
    model = asm.resolve()
    joint = model.joints[0]
    assert isinstance(joint, ww.BoxJoint)
    assert joint.fingers == fingers
    assert cuts(model, a) == [f"box joint, {described[0]}, 12 long"]
    assert cuts(model, b) == [f"box joint, {described[1]}, 20 long"]
    assert interference(model) == pytest.approx(0, abs=1e-6)
    # The fingers fill the corner: no gaps.
    total = model[a].shape.volume + model[b].shape.volume
    assert total == pytest.approx(312 * 100 * 20 + 220 * 100 * 12 - 12 * 100 * 20)
    # Part b stands beyond part a's end, against its inside face, reaching through it.
    assert bbox(model[b].placed_shape) == (300, 0, -220, 312, 100, 0)
    with pytest.raises(ValueError, match="at least two fingers"):
        ww.BoxJoint(a.right_end, b.left_end, fingers=1).with_defaults()


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


@pytest.mark.parametrize("edges", [("front_edge",), ("front_edge", "back_edge")])
def test_mitred_corner_dovetail(edges: tuple[str, ...]) -> None:
    asm = ww.Assembly("test")
    pins = asm.add(ww.Board("pins", OAK, length=300, width=100))
    tails = asm.add(ww.Board("tails", OAK, length=200, width=100))
    mitred = tuple(getattr(pins, edge) for edge in edges)
    asm.join(
        ww.MitredCornerDovetail(
            tails=tails.left_end, pins=pins.right_end, tail_count=2, mitred=mitred, mitre_width=15
        )
    )
    model = asm.resolve()
    at = ", ".join(f"pins.{edge}" for edge in edges)
    assert cuts(model, pins) == [f"sockets for 2 dovetails, mitred 15 mm at {at}"]
    assert cuts(model, tails)[0].endswith(f"mitred 15 mm at {at.replace('pins', 'tails')}")
    assert interference(model) == pytest.approx(0, abs=1e-6)
    total = model[pins].shape.volume + model[tails].shape.volume
    assert total == pytest.approx((320 + 220 - 20) * 100 * 20)
    # In the mitred strips each board has half of the corner, on its side of the diagonal.
    for y0 in [0, 85][: len(edges)]:
        strip = bd.Pos(300, y0, -20) * bd.Box(20, 15, 20, align=(bd.Align.MIN,) * 3)
        assert (model[pins].shape & strip).volume == pytest.approx(strip.volume / 2)
    # The outside face of the pin board shows the mitre: its corner is whole at the edge.
    edge = bd.Pos(300, 0, -0.1) * bd.Box(20, 15, 0.1, align=(bd.Align.MIN,) * 3)
    assert (model[pins].shape & edge).volume == pytest.approx(edge.volume, rel=0.01)
    narrow = asm.add(ww.Board("narrow", OAK, length=200, width=80))
    with pytest.raises(ValueError, match="equally wide"):
        ww.MitredCornerDovetail(tails=tails.right_end, pins=narrow.left_end)


@pytest.mark.parametrize("tail_thickness", [20, 15])
def test_blind_mitred_dovetail(tail_thickness: float) -> None:
    asm = ww.Assembly("test")
    pins = asm.add(ww.Board("pins", OAK, length=300, width=100))
    tails = asm.add(ww.Board("tails", ww.Stock.board(tail_thickness, "oak"), length=200, width=100))
    asm.join(ww.BlindMitredDovetail(tails=tails.left_end, pins=pins.right_end, tail_count=2))
    model = asm.resolve()
    joint = model.joints[0]
    assert isinstance(joint, ww.BlindMitredDovetail)
    assert (joint.lap, joint.tail_lip()) == (5, pytest.approx(5 * tail_thickness / 20))
    assert cuts(model, pins) == [
        "sockets for 2 blind mitred dovetails, 15 deep, lap 5, mitred 10 mm at the edges"
    ]
    assert interference(model) == pytest.approx(0, abs=1e-6)
    t = tail_thickness
    # Both boards reach through each other and fill the corner: no gaps.
    total = model[pins].shape.volume + model[tails].shape.volume
    assert total == pytest.approx((300 + t) * 100 * 20 + 220 * 100 * t - t * 100 * 20)
    assert bbox(model[tails].placed_shape) == (300, 0, -200 - 20, 300 + t, 100, 0)

    def share(region: bd.Part) -> float:
        """Part of a thin region of the corner held by the pin board."""
        return (model[pins].shape & region).volume / region.volume

    # On the outside faces only the mitre shows: the pin board's face runs out to
    # the corner over the tail board's end, the tail board's face over the pins.
    d = 0.01
    assert share(bd.Pos(300, 0, -d) * bd.Box(t, 100, d, align=(bd.Align.MIN,) * 3)) > 0.99
    assert share(bd.Pos(300 + t - d, 0, -20) * bd.Box(d, 100, 20, align=(bd.Align.MIN,) * 3)) < 0.01
    # On the edges the corner is mitred through the whole thickness.
    for y0 in (0, 100 - d):
        edge = bd.Pos(300, y0, -20) * bd.Box(t, d, 20, align=(bd.Align.MIN,) * 3)
        assert share(edge) == pytest.approx(0.5)
    narrow = asm.add(ww.Board("narrow", OAK, length=200, width=80))
    with pytest.raises(ValueError, match="equally wide"):
        ww.BlindMitredDovetail(tails=tails.right_end, pins=narrow.left_end)


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


def test_tee_bridle() -> None:
    asm = ww.Assembly("test")
    stile = asm.add(ww.Board("stile", OAK, length=400, width=50))
    rail = asm.add(ww.Board("rail", OAK, length=300, width=40))
    asm.join(ww.TeeBridle(slot=rail.left_end, edge=stile.back_edge))
    model = asm.resolve()
    assert cuts(model, rail) == ["slot mortise 8 mm, 50 deep, in rail.left_end"]
    assert cuts(model, stile) == [
        "dado 40 mm, 6 deep, in stile.top_face",
        "dado 40 mm, 6 deep, in stile.bottom_face",
    ]
    # The rail reaches across the stile, its end flush with the front edge.
    box = model[rail].placed_shape.bounding_box()
    assert pytest.approx((0, 300, 180, 220)) == (box.min.Y, box.max.Y, box.min.X, box.max.X)
    assert model[stile].shape.volume == pytest.approx(400 * 50 * 20 - 2 * 40 * 50 * 6)
    assert model[rail].shape.volume == pytest.approx(300 * 40 * 20 - 50 * 40 * 8)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_tee_bridle_with_an_offset_slot() -> None:
    asm, stile, rail = stile_and_rail()
    asm.join(ww.TeeBridle(slot=rail.left_end, edge=stile.back_edge, slot_offset=4))
    model = asm.resolve()
    assert cuts(model, stile) == [
        "dado 40 mm, 4 deep, in stile.top_face",
        "dado 40 mm, 8 deep, in stile.bottom_face",
    ]
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_tee_bridle_needs_an_end_and_an_edge() -> None:
    _, stile, rail = stile_and_rail()
    with pytest.raises(ValueError, match="slot is in an end"):
        ww.TeeBridle(slot=rail.front_edge, edge=stile.back_edge)
    with pytest.raises(ValueError, match="straddles an edge"):
        ww.TeeBridle(slot=rail.left_end, edge=stile.top_face)


@pytest.mark.parametrize("through", [False, True])
def test_rabbet_joint_through(through: bool) -> None:
    asm = ww.Assembly("test")
    wall = asm.add(ww.Board("wall", OAK, length=300, width=100))
    bottom = asm.add(ww.Board("bottom", OAK, length=200, width=150))
    asm.join(
        ww.RabbetJoint(
            rabbet=wall.bottom_face, end=bottom.front_edge, at=wall.front_edge, through=through
        )
    )
    model = asm.resolve()
    expected = "rabbet 20 mm, 10 deep" if through else "notch 200 x 20 mm, 10 deep"
    assert cuts(model, wall) == [f"{expected}, in wall.bottom_face at wall.front_edge"]


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


def test_loose_tenon() -> None:
    asm, stile, rail = stile_and_rail(rail_width=60)
    tenon = asm.add(ww.Board("tenon", ww.Stock.board(6, "oak"), length=50, width=30))
    asm.join(
        ww.LooseTenon(
            stile.back_edge,
            rail.left_end,
            tenon,
            depth=30,
            tenon_position=ww.offset(10, rail.front_edge),
            tenon_offset=4,
        )
    )
    model = asm.resolve()
    assert cuts(model, stile) == ["mortise 30 x 6 mm, 32 deep, in stile.back_edge"]
    assert cuts(model, rail) == ["mortise 30 x 6 mm, 22 deep, in rail.left_end"]
    assert model[tenon].size == (50, 30, 6)
    # The rail stands on the back edge of the stile, centered along it, its
    # front edge towards the stile's right end.
    assert bbox(model[rail].placed_shape) == (120, 40, -20, 180, 240, 0)
    # 30 mm into the stile, 10 mm from the rail's front edge, 4 mm below the faces.
    assert bbox(model[tenon].placed_shape) == (140, 10, -10, 170, 60, -4)
    assert model[stile].shape.volume == pytest.approx(300 * 40 * 20 - 30 * 6 * 32)
    assert interference(model) == pytest.approx(0, abs=1e-6)


@pytest.mark.parametrize("through", [True, False])
def test_loose_tongue(through: bool) -> None:
    asm = ww.Assembly("test")
    a = asm.add(ww.Board("a", OAK, length=300, width=100))
    b = asm.add(ww.Board("b", OAK, length=300, width=100))
    tongue = asm.add(ww.Board("tongue", ww.Stock.board(6, "oak"), length=260, width=24))
    asm.join(ww.LooseTongue(a.back_edge, b.front_edge, tongue, depth=10, through=through))
    model = asm.resolve()
    if through:
        assert cuts(model, a) == ["groove 6 mm, 11 deep, in a.back_edge"]
        assert cuts(model, b) == ["groove 6 mm, 15 deep, in b.front_edge"]
    else:
        stops = "20 mm short of {0}.left_end and 20 mm short of {0}.right_end"
        assert cuts(model, a) == [
            "stopped groove 6 mm, 11 deep, in a.back_edge, " + stops.format("a")
        ]
        assert cuts(model, b) == [
            "stopped groove 6 mm, 15 deep, in b.front_edge, " + stops.format("b")
        ]
    assert cuts(model, tongue) == []
    # Centered along the joint and across the thickness, 10 mm into part a.
    assert bbox(model[tongue].placed_shape) == (20, 90, -13, 280, 114, -7)
    length = 300 if through else 260
    assert model[a].shape.volume == pytest.approx(300 * 100 * 20 - length * 6 * 11)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_loose_tongue_placed_along_and_across() -> None:
    asm = ww.Assembly("test")
    a = asm.add(ww.Board("a", OAK, length=300, width=100))
    b = asm.add(ww.Board("b", OAK, length=300, width=100))
    tongue = asm.add(ww.Board("tongue", ww.Stock.board(6, "oak"), length=200, width=20))
    asm.join(
        ww.LooseTongue(
            a.back_edge,
            b.front_edge,
            tongue,
            through=False,
            tongue_position=ww.offset(30),
            tongue_offset=4,
        )
    )
    model = asm.resolve()
    assert bbox(model[tongue].placed_shape) == (30, 90, -10, 230, 110, -4)
    assert cuts(model, a) == [
        "stopped groove 6 mm, 11 deep, in a.back_edge, "
        "30 mm short of a.left_end and 70 mm short of a.right_end"
    ]
    with pytest.raises(ValueError, match="into both parts"):
        ww.LooseTongue(a.back_edge, b.front_edge, tongue, depth=20).with_defaults()


def test_loose_tenon_must_be_added() -> None:
    asm, stile, rail = stile_and_rail()
    tenon = ww.Board("tenon", ww.Stock.board(6, "oak"), length=50, width=30)
    asm.join(ww.LooseTenon(stile.back_edge, rail.left_end, tenon))
    with pytest.raises(ValueError, match="tenon is joined but not added"):
        asm.resolve()


def test_twin_tenons() -> None:
    asm = ww.Assembly("test")
    stile = asm.add(ww.Board("stile", OAK, length=300, width=60))
    rail = asm.add(ww.Board("rail", OAK, length=200, width=110))
    asm.join(ww.MortiseTenon(tenon=rail.left_end, mortise=stile.back_edge, shoulder=10, tenons=2))
    model = asm.resolve()
    assert model.joints[0].tenon_gap == 30  # as wide as the tenons
    assert cuts(model, stile) == ["mortise 30 x 8 mm, 42 deep, in stile.back_edge"] * 2
    assert cuts(model, rail) == ["2 tenons 30 x 8 mm, 40 long, 30 apart, on rail.left_end"]
    assert model[rail].shape.volume == pytest.approx(200 * 110 * 20 + 2 * 30 * 8 * 40)
    assert model[stile].shape.volume == pytest.approx(300 * 60 * 20 - 2 * 30 * 8 * 42)
    # The mortises are 30 mm apart along the stile, centered on the rail.
    mortises = sorted(cut.ranges()[0] for cut in model[stile].cuts)
    assert mortises == [(105, 135), (165, 195)]
    assert interference(model) == pytest.approx(0, abs=1e-6)


THICK = ww.Stock.board(45, "oak")


def post_and_thick_rail(rail_width: float = 45) -> tuple[ww.Assembly, ww.Board, ww.Board]:
    asm = ww.Assembly("test")
    post = asm.add(ww.Board("post", THICK, length=400, width=60))
    rail = asm.add(ww.Board("rail", THICK, length=300, width=rail_width))
    return asm, post, rail


def test_tenons_across_the_thickness() -> None:
    asm, post, rail = post_and_thick_rail()
    asm.join(ww.MortiseTenon(tenon=rail.left_end, mortise=post.back_edge, thickness_tenons=2))
    model = asm.resolve()
    joint = model.joints[0]
    # A fifth of the rail each, snapped to a chisel; the gap as thick.
    assert (joint.tenon_thickness, joint.thickness_gap) == (10, 10)
    assert cuts(model, post) == ["mortise 35 x 10 mm, 42 deep, in post.back_edge"] * 2
    assert cuts(model, rail) == [
        "2 tenons 35 x 10 mm, 40 long, 10 apart across the thickness, on rail.left_end"
    ]
    assert model[rail].shape.volume == pytest.approx(300 * 45 * 45 + 2 * 35 * 10 * 40)
    assert model[post].shape.volume == pytest.approx(400 * 60 * 45 - 2 * 35 * 10 * 42)
    # Each in its own mortise, 7.5 mm in from the faces.
    mortises = sorted(cut.ranges()[2] for cut in model[post].cuts)
    assert mortises == [(-37.5, -27.5), (-17.5, -7.5)]
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_grid_of_chamfered_through_tenons() -> None:
    asm, post, rail = post_and_thick_rail()
    asm.join(
        ww.MortiseTenon(
            tenon=rail.left_end,
            mortise=post.back_edge,
            shoulder=7.5,
            tenons=2,
            thickness_tenons=2,
            tenon_length=63,  # 3 mm proud
            tenon_chamfer=2,
        )
    )
    model = asm.resolve()
    assert model.joints[0].tenon_gap == 10
    assert cuts(model, post) == ["through mortise 10 x 10 mm in post.back_edge"] * 4
    assert cuts(model, rail) == [
        "4 tenons 10 x 10 mm, 63 long, 2 across the width 10 apart, "
        "2 across the thickness 10 apart, end chamfered 2 mm, on rail.left_end"
    ]
    # Each tenon loses its own chamfers, not into the tenons beside it.
    chamfers = 2 * (10 + 10) * 2 * 2 / 2 - 4 * 2**3 / 3
    tenons = 4 * (10 * 10 * 63 - chamfers)
    assert model[rail].shape.volume == pytest.approx(300 * 45 * 45 + tenons)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_haunched_and_mitred_tenons_across_the_thickness() -> None:
    asm, post, rail = post_and_thick_rail(rail_width=90)
    asm.join(
        ww.MortiseTenon(
            tenon=rail.left_end,
            mortise=post.back_edge,
            position=ww.offset(20, post.right_end),
            shoulder=(20, 5),
            thickness_tenons=2,
            haunch=rail.front_edge,
            haunch_length=10,
        )
    )
    model = asm.resolve()
    # A haunch beside each tenon, each in its own haunch mortise.
    assert cuts(model, post)[2:] == ["haunch mortise 20 x 10 mm, 10 deep, in post.back_edge"] * 2
    assert model[rail].shape.volume == pytest.approx(
        300 * 90 * 45 + 2 * 65 * 10 * 40 + 2 * 20 * 10 * 10
    )
    assert interference(model) == pytest.approx(0, abs=1e-6)

    asm, post, rail = post_and_thick_rail(rail_width=90)
    asm.join(
        ww.MortiseTenon(
            tenon=rail.left_end,
            mortise=post.back_edge,
            thickness_tenons=2,
            tenon_length=30,
            mitre=rail.top_face,
        )
    )
    model = asm.resolve()
    # One mitre across both, from 30 mm long at the bottom cheek to nothing
    # at the top one: half of the tenons is left.
    assert model[rail].shape.volume == pytest.approx(300 * 90 * 45 + 2 * 80 * 10 * 30 / 2)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_wedged_tenons_across_the_thickness() -> None:
    asm, post, rail = post_and_thick_rail(rail_width=90)
    stock = ww.Stock.board(10, "oak")
    wedges = tuple(asm.add(ww.Board(f"wedge_{i}", stock, length=40, width=5)) for i in range(4))
    asm.join(
        ww.WedgedMortiseTenon(
            tenon=rail.left_end,
            mortise=post.back_edge,
            shoulder=10,
            thickness_tenons=2,
            wedges=wedges,
        )
    )
    model = asm.resolve()
    assert cuts(model, rail) == [
        "2 tenons 70 x 10 mm, 60 long, 10 apart across the thickness, "
        "2 saw kerfs each 2 mm, 40 deep, for wedges, on rail.left_end"
    ]
    # Both tenons spread at their ends, only within their thickness.
    flares = 2 * (2 * 3 * 40 / 2 * 10)
    wedge = (2 + 5) / 2 * 40 * 10
    assert model[post].shape.volume == pytest.approx(400 * 60 * 45 - 2 * 70 * 10 * 60 - flares)
    tenons = 2 * 70 * 10 * 60 + flares - 4 * wedge
    assert model[rail].shape.volume == pytest.approx(300 * 90 * 45 + tenons)
    # The top tenon's wedges first.
    heights = [model[w].placed_shape.bounding_box() for w in wedges]
    assert [(box.min.Z, box.max.Z) for box in heights] == pytest.approx(
        [(-17.5, -7.5), (-17.5, -7.5), (-37.5, -27.5), (-37.5, -27.5)]
    )
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_three_chamfered_through_tenons_with_a_haunch() -> None:
    asm = ww.Assembly("test")
    stile = asm.add(ww.Board("stile", OAK, length=300, width=60))
    rail = asm.add(ww.Board("rail", OAK, length=200, width=110))
    asm.join(
        ww.MortiseTenon(
            tenon=rail.left_end,
            mortise=stile.back_edge,
            position=ww.flush_with(stile.right_end),
            shoulder=(15, 5),
            tenons=3,
            tenon_gap=15,
            tenon_length=62,
            tenon_chamfer=2,
            haunch=rail.front_edge,
            haunch_length=10,
        )
    )
    model = asm.resolve()
    assert cuts(model, rail) == [
        "3 haunched tenons 20 x 8 mm, 62 long, 15 apart, haunch 10 long, "
        "end chamfered 2 mm, on rail.left_end"
    ]
    assert cuts(model, stile)[:3] == ["through mortise 20 x 8 mm in stile.back_edge"] * 3
    # Each tenon loses four chamfers around its end (with the corners counted twice).
    chamfers = 2 * (20 + 8) * 2 * 2 / 2 - 4 * 2**3 / 3
    tenons = 3 * 20 * 8 * 62 + 15 * 8 * 10
    assert model[rail].shape.volume == pytest.approx(200 * 110 * 20 + tenons - 3 * chamfers)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_twin_tenons_with_mitred_shoulders() -> None:
    stock = ww.Stock.board(30, "oak")
    asm = ww.Assembly("test")
    stile = asm.add(ww.Board("stile", stock, length=300, width=45))
    rail = asm.add(ww.Board("rail", stock, length=200, width=90))
    asm.join(ww.MitredShoulderTenon(tenon=rail.left_end, mortise=stile.back_edge, tenons=2))
    model = asm.resolve()
    # Both mortises are cut from the side, through the notch.
    assert cuts(model, stile) == [
        "mortise 25 x 10 mm, 37 deep, in stile.back_edge",
        "mortise 25 x 10 mm, 37 deep, in stile.back_edge",
        "notch 90 long, 15 deep, mitred at both ends, in stile.back_edge",
    ]
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_wedged_through_tenon() -> None:
    asm = ww.Assembly("test")
    stile = asm.add(ww.Board("stile", OAK, length=300, width=60))
    rail = asm.add(ww.Board("rail", OAK, length=200, width=60))
    stock = ww.Stock.board(8, "oak")
    wedges = tuple(asm.add(ww.Board(f"wedge_{i}", stock, length=40, width=5)) for i in range(2))
    asm.join(
        ww.WedgedMortiseTenon(
            tenon=rail.left_end, mortise=stile.back_edge, shoulder=10, wedges=wedges
        )
    )
    model = asm.resolve()
    joint = model.joints[0]
    assert (joint.tenon_thickness, joint.tenon_length) == (8, 60)  # from the wedges, through
    assert cuts(model, stile) == [
        "through mortise 40 x 8 mm in stile.back_edge",
        "mortise flared 3 mm at the ends over 40, in stile.back_edge",
    ]
    assert cuts(model, rail) == [
        "tenon 40 x 8 mm, 60 long, 2 saw kerfs 2 mm, 40 deep, for wedges, on rail.left_end"
    ]
    assert cuts(model, wedges[0]) == ["taper 3 mm on wedge_0.back_edge towards wedge_0.right_end"]
    # The tenon spreads 3 mm at each end over 40 mm; the wedges fill the kerfs.
    flares = 2 * 3 * 40 / 2 * 8
    wedge = (2 + 5) / 2 * 40 * 8
    assert model[wedges[0]].shape.volume == pytest.approx(wedge)
    assert model[stile].shape.volume == pytest.approx(300 * 60 * 20 - 40 * 8 * 60 - flares)
    tenon = 40 * 8 * 60 + flares - 2 * wedge
    assert model[rail].shape.volume == pytest.approx(200 * 60 * 20 + tenon)
    # The wedges lie flush with the stile's front edge, in kerfs 8 mm in from
    # the edges of the tenon (at 130 and 170), the outer parts spread outwards;
    # the first one towards the rail's front edge, at the stile's right end.
    assert bbox(model[wedges[0]].placed_shape) == (160, 0, -14, 165, 40, -6)
    assert bbox(model[wedges[1]].placed_shape) == (135, 0, -14, 140, 40, -6)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_twin_wedged_tenons_proud_with_a_wedge_each() -> None:
    asm = ww.Assembly("test")
    stile = asm.add(ww.Board("stile", OAK, length=300, width=60))
    rail = asm.add(ww.Board("rail", OAK, length=200, width=110))
    stock = ww.Stock.board(8, "oak")
    # 5 mm proud: the wedges are 5 mm longer than the flare.
    wedges = tuple(asm.add(ww.Board(f"wedge_{i}", stock, length=35, width=6)) for i in range(2))
    asm.join(
        ww.WedgedMortiseTenon(
            tenon=rail.left_end,
            mortise=stile.back_edge,
            shoulder=10,
            tenons=2,
            tenon_length=65,
            wedges=wedges,
        )
    )
    model = asm.resolve()
    assert cuts(model, stile)[2] == "mortises flared 2 mm at the ends over 30, in stile.back_edge"
    assert cuts(model, wedges[0]) == [
        "taper 2 mm over 30 on wedge_0.front_edge towards wedge_0.right_end",
        "taper 2 mm over 30 on wedge_0.back_edge towards wedge_0.right_end",
    ]
    flares = 2 * 2 * (2 * 30 / 2 + 2 * 5) * 8
    wedge = ((2 + 6) / 2 * 30 + 6 * 5) * 8
    assert model[wedges[0]].shape.volume == pytest.approx(wedge)
    tenons = 2 * 30 * 8 * 65 + flares - 2 * wedge
    assert model[rail].shape.volume == pytest.approx(200 * 110 * 20 + tenons)
    assert pytest.approx(-5) == model[rail].placed_shape.bounding_box().min.Y
    assert interference(model) == pytest.approx(0, abs=1e-6)


def _tusk_tenon(wedge_size: tuple[float, float, float], wedge_head: str = "right_end") -> tuple:
    stock = ww.Stock.board(40, "oak")
    asm = ww.Assembly("test")
    stile = asm.add(ww.Board("stile", stock, length=300, width=60))
    rail = asm.add(ww.Board("rail", stock, length=200, width=60))
    length, width, thickness = wedge_size
    wedge_stock = ww.Stock.board(thickness, "oak")
    wedge = asm.add(ww.Board("wedge", wedge_stock, length=length, width=width))
    joint = ww.TuskTenon(
        tenon=rail.left_end,
        mortise=stile.back_edge,
        shoulder=10,
        tenon_thickness=20,
        wedge=wedge,
        protrusion=40,
        wedge_head=getattr(stile, wedge_head),
    )
    asm.join(joint)
    return asm, stile, rail, wedge


def test_tusk_tenon_with_the_wedge_parallel_to_the_stile() -> None:
    asm, stile, rail, wedge = _tusk_tenon((80, 20, 8))
    model = asm.resolve()
    assert model.joints[0].tenon_length == 100  # through and 40 proud
    assert cuts(model, stile) == ["through mortise 40 x 20 mm in stile.back_edge"]
    assert cuts(model, rail) == [
        "tenon 40 x 20 mm, 100 long, on rail.left_end",
        "wedge mortise 8 x 20.5 to 15.5 mm through the tenon on rail.left_end, "
        "its outer end sloped 1:8, from 3 inside stile.front_edge",
    ]
    assert cuts(model, wedge) == ["taper 10 mm on wedge.back_edge towards wedge.right_end"]
    # Upright along the stile, centered on the tenon, against the stile's front edge.
    assert bbox(model[wedge].placed_shape) == (110, -20, -24, 190, 0, -16)
    assert model[wedge].shape.volume == pytest.approx((20 + 10) / 2 * 80 * 8)
    assert model[stile].shape.volume == pytest.approx(300 * 60 * 40 - 40 * 20 * 60)
    # The mortise reaches 3 mm into the stile and out to the wedge's back edge.
    mortise = 8 * 40 * (20.5 + 15.5) / 2
    assert model[rail].shape.volume == pytest.approx(200 * 60 * 40 + 40 * 20 * 100 - mortise)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_tusk_tenon_with_the_wedge_perpendicular_to_the_stile() -> None:
    asm, _, rail, wedge = _tusk_tenon((50, 20, 16), wedge_head="top_face")
    model = asm.resolve()
    assert cuts(model, rail)[1] == (
        "wedge mortise 16 x 21.1 to 18.6 mm through the tenon on rail.left_end, "
        "its outer end sloped 1:8, from 3 inside stile.front_edge"
    )
    # Through the tenon's thickness, its head up out of the stile's top face.
    assert bbox(model[wedge].placed_shape) == (142, -20, -45, 158, 0, 5)
    mortise = 16 * 20 * (21.125 + 18.625) / 2
    assert model[rail].shape.volume == pytest.approx(200 * 60 * 40 + 40 * 20 * 100 - mortise)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def _dowel_tusk_tenon(tusks: int = 1, bearings: int | None = None, **kw) -> tuple:
    asm = ww.Assembly("test")
    stile = asm.add(ww.Board("stile", ww.Stock.board(60, "oak"), length=400, width=60))
    rail = asm.add(ww.Board("rail", ww.Stock.board(30, "oak"), length=200, width=140))
    dowel = ww.Stock.rod(20, "oak")
    length = kw.pop("tusk_length", 120)
    bearing_length = kw.pop("bearing_length", 30)
    rods = tuple(asm.add(ww.Rod(f"tusk_{i + 1}", dowel, length=length)) for i in range(tusks))
    halves = tuple(
        asm.add(ww.Rod(f"bearing_{i + 1}", dowel, length=bearing_length))
        for i in range(tusks if bearings is None else bearings)
    )
    asm.join(
        ww.DowelTuskTenon(
            tenon=rail.left_end,
            mortise=stile.back_edge,
            shoulder=20,
            tenon_thickness=30,
            across=ww.centered(),
            tusks=rods,
            bearings=halves,
            tusk_head=stile.top_face,
            **kw,
        )
    )
    return asm, stile, rail, rods, halves


def test_dowel_tusk_tenon() -> None:
    asm, stile, rail, (tusk,), (bearing,) = _dowel_tusk_tenon()
    model = asm.resolve()
    # The flat, 1:12 over 60 mm, 5 deep at the tip, touches the round top of
    # the half dowel (r = 10) and lies 10 / cos over its axis there, half
    # its depth above the tusk's front edge: the hole's inner edge.
    inner = 10 / math.cos(math.atan(1 / 12)) - 2.5
    # The tenon stands out 1.5 tusk diameters beyond the hole.
    assert model.joints[0].tenon_length == pytest.approx(60 + inner + 20 + 30)
    assert cuts(model, stile) == ["through mortise 100 x 30 mm in stile.back_edge"]
    assert cuts(model, rail)[1] == (
        "a hole ø20 for tusks through the tenon on rail.left_end, parallel to "
        "stile.front_edge, 7.5 mm off it"
    )
    assert cuts(model, tusk) == [
        "flat taper 5 mm over 60 on tusk_1.front_edge towards tusk_1.right_end"
    ]
    assert cuts(model, bearing) == ["flat 20 mm wide, 10 deep, on bearing_1.front_edge"]
    # The tenon (z from -45 to -15) is centered on x = 200. The half dowel
    # lies flat on the stile's front edge (y = 0) behind the tenon, across
    # the tusk; the tusk lies parallel to the stile, its head up (the stile's
    # top face), the middle of its flat over the half dowel's axis.
    assert bbox(model[bearing].placed_shape) == (185, -10, -65, 215, 0, -45)
    assert bbox(model[tusk].placed_shape) == (190, -inner - 20, -85, 210, -inner, 35)
    for a, b in [(tusk, bearing), (bearing, stile)]:
        distance = model[a].placed_shape.distance_to(model[b].placed_shape)
        assert distance == pytest.approx(0, abs=1e-6)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_dowel_tusk_tenon_with_two_tusks_on_one_bearing() -> None:
    asm, *_, tusks, (bearing,) = _dowel_tusk_tenon(tusks=2, bearings=1, bearing_length=100)
    model = asm.resolve()
    # In the second and the fourth fifth of the 100 mm tenon.
    centers = sorted(model[t].placed_shape.bounding_box().center().X for t in tusks)
    assert centers == pytest.approx([180, 220])
    assert pytest.approx(200) == model[bearing].placed_shape.bounding_box().center().X
    for tusk in tusks:
        distance = model[tusk].placed_shape.distance_to(model[bearing].placed_shape)
        assert distance == pytest.approx(0, abs=1e-6)
    assert interference(model) == pytest.approx(0, abs=1e-6)


@pytest.mark.parametrize(
    ("kw", "message"),
    [
        (dict(tusks=0), "needs tusks"),
        (dict(bearings=0), "a bearing per tusk"),
        (dict(tusks=2, bearing_length=50), "don't fit side by side"),
        (dict(tusk_slope=4), "deeper than half the dowel"),
        (dict(protrusion=25), "run out of the end of the tenon"),
        (dict(tusks=3), "don't fit side by side"),  # 100 / 7 < 20
        (dict(tusk_length=50), "reach through the tenon"),
    ],
)
def test_dowel_tusk_tenon_must_fit(kw: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        asm, *_ = _dowel_tusk_tenon(**kw)
        asm.resolve()


def test_tusk_tenon_wedge_must_fit() -> None:
    with pytest.raises(ValueError, match="longer than the tenon"):
        _tusk_tenon((30, 20, 8))[0].resolve()
    with pytest.raises(ValueError, match="thinner than the tenon"):
        _tusk_tenon((80, 20, 20))[0].resolve()
    with pytest.raises(ValueError, match="runs out of the end"):
        _tusk_tenon((80, 45, 8))[0].resolve()
    with pytest.raises(ValueError, match="next to"):
        _tusk_tenon((80, 20, 8), wedge_head="front_edge")


def test_wedges_must_fit_the_tenon() -> None:
    asm, stile, rail = stile_and_rail(rail_width=60)
    wedge = asm.add(ww.Board("wedge", ww.Stock.board(6, "oak"), length=40, width=5))
    asm.join(
        ww.WedgedMortiseTenon(
            tenon=rail.left_end, mortise=stile.back_edge, tenon_thickness=8, wedges=(wedge,)
        )
    )
    with pytest.raises(ValueError, match="as thick as the tenon"):
        asm.resolve()
    with pytest.raises(ValueError, match="spread wider than its shoulders"):
        ww.WedgedMortiseTenon(
            tenon=rail.left_end, mortise=stile.back_edge, shoulder=1, wedges=(wedge,)
        ).with_defaults().tenon_cut()


# --- Round joints -----------------------------------------------------------

ROD = ww.Stock.rod(25, "oak")
LEG = ww.Stock.board(45, "oak")


def leg_and_rod(stock: ww.Stock = ROD) -> tuple[ww.Assembly, ww.Board, ww.Rod]:
    asm = ww.Assembly("test")
    leg = asm.add(ww.Board("leg", LEG, length=400, width=45))
    rod = asm.add(ww.Rod("rod", stock, length=300))
    return asm, leg, rod


def test_whole_rod_in_a_blind_hole() -> None:
    asm, leg, rod = leg_and_rod()
    asm.join(ww.RoundMortiseTenon(tenon=rod.left_end, mortise=leg.back_edge))
    model = asm.resolve()
    assert cuts(model, leg) == ["hole ø25, 32 deep, in leg.back_edge, centered"]
    assert cuts(model, rod) == []
    assert model[rod].size == (330, 25, 25)
    # Centered on the leg both ways, 30 into it.
    assert bbox(model[rod].placed_shape) == (187.5, 15, -35, 212.5, 345, -10)
    removed = 400 * 45 * 45 - model[leg].shape.volume
    assert removed == pytest.approx(math.pi * 12.5**2 * 32)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_round_tenon_on_square_stock_through() -> None:
    asm = ww.Assembly("test")
    seat = asm.add(ww.Board("seat", ww.Stock.board(30, "oak"), length=300, width=300))
    leg = asm.add(ww.Board("leg", LEG, length=400, width=45))
    asm.join(ww.RoundMortiseTenon(tenon=leg.right_end, mortise=seat.bottom_face, length=30))
    model = asm.resolve()
    # About 0.6 of the leg, snapped down to a drill bit.
    assert cuts(model, leg) == ["round tenon ø25, 30 long, on leg.right_end"]
    assert cuts(model, seat) == ["through hole ø25, in seat.bottom_face, centered"]
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_tapered_round_tenon_in_a_reamed_hole() -> None:
    asm, leg, rod = leg_and_rod(ww.Stock.rod(30, "oak"))
    asm.join(
        ww.RoundMortiseTenon(
            tenon=rod.left_end, mortise=leg.back_edge, diameter=20, tip_diameter=16, length=30
        )
    )
    model = asm.resolve()
    # The hole tapers on, 2 deeper than the tenon.
    hole = "tapered hole ø20 to ø15.7333, 32 deep, in leg.back_edge, centered"
    assert cuts(model, leg) == [hole]
    assert cuts(model, rod) == ["round tenon ø20, 30 long, tapered to ø16, on rod.left_end"]
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_round_tenon_into_a_rod() -> None:
    asm = ww.Assembly("test")
    leg = asm.add(ww.Rod("leg", ww.Stock.rod(40, "oak"), length=400))
    rung = asm.add(ww.Rod("rung", ROD, length=300))
    asm.join(
        ww.RoundMortiseTenon(tenon=rung.left_end, mortise=leg.back_edge, diameter=16, length=25)
    )
    model = asm.resolve()
    assert cuts(model, leg) == ["hole ø16, 27 deep, in leg.back_edge, centered"]
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_round_tenon_is_on_an_end() -> None:
    asm, leg, rod = leg_and_rod()
    asm.join(ww.RoundMortiseTenon(tenon=rod.top_face, mortise=leg.back_edge))
    with pytest.raises(ValueError, match="on an end, not on rod"):
        asm.resolve()


def test_wedged_round_tenon() -> None:
    asm = ww.Assembly("test")
    seat = asm.add(ww.Board("seat", ww.Stock.board(30, "oak"), length=300, width=300))
    leg = asm.add(ww.Rod("leg", ww.Stock.rod(40, "oak"), length=400))
    wedge = asm.add(ww.Board("wedge", OAK, length=20, width=6))
    asm.join(
        ww.WedgedRoundMortiseTenon(
            tenon=leg.right_end, mortise=seat.bottom_face, diameter=25, wedge=wedge
        )
    )
    model = asm.resolve()
    assert cuts(model, seat) == ["through hole ø25, in seat.bottom_face, centered"]
    assert cuts(model, wedge) == [
        "taper 2 mm on wedge.front_edge towards wedge.right_end",
        "taper 2 mm on wedge.back_edge towards wedge.right_end",
    ]
    # The wedge's head is flush with the top of the seat, across its grain
    # (the kerf runs along y, the wedge spreads the tenon along the seat's length).
    assert bbox(model[wedge].placed_shape) == (147, 140, -20, 153, 160, 0)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_wedged_round_tenon_goes_through() -> None:
    asm = ww.Assembly("test")
    seat = asm.add(ww.Board("seat", ww.Stock.board(30, "oak"), length=300, width=300))
    leg = asm.add(ww.Rod("leg", ww.Stock.rod(40, "oak"), length=400))
    wedge = asm.add(ww.Board("wedge", OAK, length=15, width=6))
    asm.join(
        ww.WedgedRoundMortiseTenon(
            tenon=leg.right_end, mortise=seat.bottom_face, diameter=25, wedge=wedge, length=20
        )
    )
    with pytest.raises(ValueError, match="goes through"):
        asm.resolve()


# --- Dowels, pegs and screws -------------------------------------------------

DOWEL = ww.Stock.rod(8, "oak")


def test_dowels_in_an_edge_joint() -> None:
    asm = ww.Assembly("test")
    a = asm.add(ww.Board("a", OAK, length=400, width=100))
    b = asm.add(ww.Board("b", OAK, length=400, width=100))
    dowels = tuple(asm.add(ww.Rod(f"dowel_{i}", DOWEL, length=30)) for i in range(2))
    asm.join(ww.Dowels(a.back_edge, b.front_edge, dowels, depth=12))
    model = asm.resolve()
    assert cuts(model, a) == [
        "dowel hole ø8, 13 deep, in a.back_edge, 133.333 from a.left_end, centered",
        "dowel hole ø8, 13 deep, in a.back_edge, 266.667 from a.left_end, centered",
    ]
    assert cuts(model, b)[0] == (
        "dowel hole ø8, 19 deep, in b.front_edge, 133.333 from b.left_end, centered"
    )
    # 12 into a, the rest into b, in the middle of the thickness.
    assert bbox(model[dowels[0]].placed_shape) == (400 / 3 - 4, 88, -14, 400 / 3 + 4, 118, -6)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_dowels_errors() -> None:
    asm = ww.Assembly("test")
    a = asm.add(ww.Board("a", OAK, length=400, width=100))
    b = asm.add(ww.Board("b", OAK, length=400, width=100))
    short = ww.Rod("short", DOWEL, length=20)
    long = ww.Rod("long", DOWEL, length=30)
    with pytest.raises(ValueError, match="same size"):
        ww.Dowels(a.back_edge, b.front_edge, (short, long))
    with pytest.raises(ValueError, match="end or an edge"):
        ww.Dowels(a.top_face, b.bottom_face, (long,))
    with pytest.raises(ValueError, match="an offset for each"):
        ww.Dowels(a.back_edge, b.front_edge, (long,), offsets=(10, 20))


def pegged(drawbore: float = 0) -> tuple[ww.ResolvedModel, ww.Board, ww.Board, ww.Rod]:
    asm = ww.Assembly("test")
    stock = ww.Stock.board(30, "oak")
    stile = asm.add(ww.Board("stile", stock, length=600, width=60))
    rail = asm.add(ww.Board("rail", stock, length=300, width=60))
    peg = asm.add(ww.Rod("peg", DOWEL, length=34))
    asm.join(
        ww.PeggedMortiseTenon(
            tenon=rail.left_end,
            mortise=stile.back_edge,
            tenon_length=40,
            peg=peg,
            peg_distance=12,
            drawbore=drawbore,
        )
    )
    return asm.resolve(), stile, rail, peg


def test_pinned_mortise_tenon() -> None:
    model, stile, rail, peg = pegged()
    assert cuts(model, stile)[-1] == (
        "peg hole ø8, in stile.top_face, 48 from stile.front_edge, centered"
    )
    assert (
        cuts(model, rail)[-1]
        == "peg hole ø8 through the tenon on rail.left_end, 12 from the shoulder"
    )
    # Through the stile, 2 proud of both faces.
    assert bbox(model[peg].placed_shape) == (296, 44, -32, 304, 52, 2)
    assert interference(model) == pytest.approx(0, abs=1e-6)
    removed = 300 * 60 * 30 + 40 * 50 * 10 - model[rail].shape.volume
    assert removed == pytest.approx(math.pi * 16 * 10)


def test_drawbored_mortise_tenon_notes_the_offset() -> None:
    model, _, rail, _ = pegged(drawbore=1.5)
    assert cuts(model, rail)[-1].endswith("drawbored: drilled 1.5 mm closer to the shoulder")


def test_screws_cut_parts_placed_by_other_joints() -> None:
    asm = ww.Assembly("test")
    board = asm.add(ww.Board("board", OAK, length=500, width=150))
    batten = asm.add(ww.Board("batten", OAK, length=400, width=60))
    # Declared before the joint placing the batten.
    asm.join(ww.Screw(batten.top_face, into=board, length=30, at={batten.left_end: 40}))
    asm.join(ww.Butt(board.top_face, batten.bottom_face, across=ww.centered()))
    model = asm.resolve()
    assert cuts(model, batten) == [
        "clearance hole ø4.5, countersunk ø8, 90 deg, in batten.top_face, "
        "40 from batten.left_end, centered, for a 4 x 30 screw"
    ]
    assert cuts(model, board) == [
        "pilot hole ø3, 10 deep, drill point 118 deg, in board.top_face, "
        "90 from board.left_end, centered, for a 4 x 30 screw"
    ]

    asm.joints[0] = ww.Screw(batten.top_face, into=board, length=45)
    with pytest.raises(ValueError, match="comes out of board"):
        asm.resolve()


def test_wedge_of_a_round_tenon_fits_within_it() -> None:
    asm = ww.Assembly("test")
    seat = asm.add(ww.Board("seat", ww.Stock.board(30, "oak"), length=300, width=300))
    leg = asm.add(ww.Rod("leg", ww.Stock.rod(40, "oak"), length=400))
    wedge = asm.add(ww.Board("wedge", ww.Stock.board(25, "oak"), length=20, width=6))
    asm.join(
        ww.WedgedRoundMortiseTenon(
            tenon=leg.right_end, mortise=seat.bottom_face, diameter=25, wedge=wedge
        )
    )
    with pytest.raises(ValueError, match="corners must lie within"):
        asm.resolve()

    asm.parts[-1] = wedge = ww.Board("wedge", ww.Stock.board(24, "oak"), length=20, width=6)
    asm.joints[0] = replace(asm.joints[0], wedge=wedge)
    model = asm.resolve()
    # The tenon is straight; the kerf, opened to the wedge's shape, is a strip
    # of the circle from 2 wide at its bottom to 6 at the top, over 20.
    r = 12.5

    def strip(w: float) -> float:  # of the circle, |y| <= w
        return 2 * (w * math.sqrt(r * r - w * w) + r * r * math.asin(w / r))

    n = 1000
    kerf = sum(strip(1 + 2 * (i + 0.5) / n) for i in range(n)) * 20 / n
    tenon = math.pi * r * r * 30 - kerf
    assert model[leg].shape.volume == pytest.approx(math.pi * 400 * 400 + tenon, rel=1e-6)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_round_tenon_through_a_batten_with_a_gap() -> None:
    asm = ww.Assembly("test")
    seat = asm.add(ww.Board("seat", ww.Stock.board(30, "oak"), length=300, width=300))
    batten = asm.add(ww.Board("batten", OAK, length=300, width=90))
    leg = asm.add(ww.Rod("leg", ww.Stock.rod(40, "oak"), length=400))
    asm.join(ww.Butt(seat.bottom_face, batten.top_face, across=ww.centered()))
    # The shoulder bears on the batten; the tenon goes on through the seat.
    asm.join(
        ww.RoundMortiseTenon(
            tenon=leg.right_end, mortise=seat.bottom_face, diameter=25, length=50, gap=20
        )
    )
    asm.join(ww.Bore(batten, leg.right_end, diameter=25))
    model = asm.resolve()
    assert cuts(model, seat) == ["through hole ø25, in seat.bottom_face, centered"]
    assert cuts(model, batten) == [
        "through hole ø25, in batten.bottom_face, centered, for the tenon on leg.right_end"
    ]
    assert cuts(model, leg) == ["round tenon ø25, 50 long, on leg.right_end"]
    assert bbox(model[leg].placed_shape) == (130, 130, -450, 170, 170, 0)
    hole = math.pi * 12.5**2
    assert model[batten].shape.volume == pytest.approx(300 * 90 * 20 - hole * 20)
    assert model[leg].shape.volume == pytest.approx(math.pi * 20**2 * 400 + hole * 50)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_bore_and_gap_checks() -> None:
    asm = ww.Assembly("test")
    seat = asm.add(ww.Board("seat", ww.Stock.board(30, "oak"), length=300, width=300))
    leg = asm.add(ww.Rod("leg", ww.Stock.rod(40, "oak"), length=400))
    asm.join(ww.RoundMortiseTenon(tenon=leg.right_end, mortise=seat.bottom_face, gap=-1))
    with pytest.raises(ValueError, match="shoulder can't be inside"):
        asm.resolve()
    asm.joints[0] = ww.RoundMortiseTenon(
        tenon=leg.right_end, mortise=seat.bottom_face, length=20, gap=20
    )
    with pytest.raises(ValueError, match="must reach into the mortised part"):
        asm.resolve()
    asm.joints[0] = ww.RoundMortiseTenon(tenon=leg.right_end, mortise=seat.bottom_face)
    asm.join(ww.Bore(seat, leg.top_face, diameter=25))
    with pytest.raises(ValueError, match=r"on an end, not on leg\.top_face"):
        asm.resolve()


BUTTERFLY = ww.Stock.board(8, "walnut")


def test_butterfly_across_a_crack() -> None:
    asm = ww.Assembly("test")
    slab = asm.add(ww.Board("slab", ww.Stock.board(30, "oak"), length=600, width=300))
    key = asm.add(ww.Board("key", BUTTERFLY, length=90, width=45))
    asm.join(ww.Butterfly(slab.top_face, key, at={slab.left_end: 150}))
    model = asm.resolve()
    assert cuts(model, slab) == [
        "butterfly mortise 90 x 45 mm, waist 15, 8 deep, in slab.top_face, "
        "150 from slab.left_end, centered"
    ]
    assert cuts(model, key) == ["shaped to a butterfly, waist 15 mm"]
    # Across the grain, flush with the top face.
    assert bbox(model[key].placed_shape) == (127.5, 105, -8, 172.5, 195, 0)
    bow_tie = 8 * (90 * 45 - 90 * 15)  # less two triangles 90 long, 15 high
    assert model[key].shape.volume == pytest.approx(bow_tie)
    assert model[slab].shape.volume == pytest.approx(600 * 300 * 30 - bow_tie)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_butterflies_across_the_joint_of_two_boards() -> None:
    asm = ww.Assembly("test")
    a = asm.add(ww.Board("a", OAK, length=600, width=200))
    b = asm.add(ww.Board("b", OAK, length=600, width=200))
    asm.join(ww.Butt(a.back_edge, b.front_edge))
    keys = [asm.add(ww.Board(f"key_{i}", BUTTERFLY, length=90, width=45)) for i in range(2)]
    for i, key in enumerate(keys):
        at = {a.left_end: 150 + 300 * i, a.back_edge: 0}
        asm.join(ww.Butterfly(a.top_face, key, at=at, other=b.top_face, angle=10 * i))
    model = asm.resolve()
    assert cuts(model, b)[0] == (
        "butterfly mortise 90 x 45 mm, waist 15, 8 deep, in b.top_face, "
        "150 from b.left_end, 200 from b.back_edge, across the joint with a"
    )
    assert cuts(model, a)[1].endswith(", turned 10 deg, across the joint with b")
    # Half of each key in each board.
    assert bbox(model[keys[0]].placed_shape) == (127.5, 155, -8, 172.5, 245, 0)
    total = 2 * 600 * 200 * 20
    assert sum(part.shape.volume for part in model.parts) == pytest.approx(total)
    assert interference(model) == pytest.approx(0, abs=1e-6)


def test_butterfly_checks() -> None:
    board = ww.Board("board", OAK, length=300, width=100)
    key = ww.Board("key", BUTTERFLY, length=90, width=45)
    with pytest.raises(ValueError, match="into a face"):
        ww.Butterfly(board.front_edge, key)
    with pytest.raises(ValueError, match="thinner than board"):
        ww.Butterfly(board.top_face, ww.Board("key", OAK, length=90, width=45))
    with pytest.raises(ValueError, match="narrower at its waist"):
        ww.Butterfly(board.top_face, key, waist=50).with_defaults()
    asm = ww.Assembly("test")
    asm.add(board)
    asm.add(key)
    asm.join(ww.Butterfly(board.top_face, key, at={board.left_end: 20}))
    with pytest.raises(ValueError, match=r"doesn't fit within board\.top_face"):
        asm.resolve()
