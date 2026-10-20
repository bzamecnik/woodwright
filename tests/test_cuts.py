import math

import build123d as bd
import pytest

import woodwright as ww

OAK = ww.Stock.board(20, "oak")


def cut_part(board: ww.Board, *cuts: ww.Cut) -> bd.Part:
    """The board with the cuts, as resolved alone in an assembly."""
    for cut in cuts:
        board.cut(cut)
    asm = ww.Assembly("test")
    asm.add(board)
    return asm.resolve()[board].shape


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
    assert tenon.allowances() == [ww.Allowance(rail.left_end, 40)]
    assert tenon.describe() == "tenon 50 x 8 mm, 40 long, on rail.left_end"
    assert cut_part(rail, tenon).volume == pytest.approx(300 * 60 * 20 + 40 * 50 * 8)


def test_tenon_with_offsets() -> None:
    rail = ww.Board("rail", OAK, length=300, width=60)
    tenon = ww.Tenon(
        rail.right_end, length=30, thickness=10, width=40, width_offset=0, thickness_offset=2
    )
    # Offsets from the front edge and from the top face.
    lo, hi = bbox(tenon.tenon())
    assert lo == (300, 0, -12)
    assert hi == (330, 40, -2)


def test_shape_cut() -> None:
    board = ww.Board("b", OAK, length=100, width=50)
    box = bd.Box(10, 10, 10)
    cut = ww.ShapeCut(board, box, name="notch")
    assert cut.part is board
    assert cut.removal() is box
    assert cut.describe() == "notch"


def board(length: float = 600, width: float = 300) -> ww.Board:
    return ww.Board("b", ww.Stock.board(40), length=length, width=width)


def test_groove() -> None:
    b = board()
    groove = ww.Groove(b.top_face, width=10, depth=20, distance=50)
    assert cut_part(b, groove).volume == pytest.approx(600 * 300 * 40 - 600 * 10 * 20)
    assert groove.ranges() == ((-ww.cuts.INF, ww.cuts.INF), (50, 60), (-20, ww.cuts.INF))
    assert groove.describe() == "groove 10 mm, 20 deep, in b.top_face"


def test_groove_centered_and_from_another_side() -> None:
    b = board()
    centered = ww.Groove(b.top_face, width=10, depth=20)
    assert centered.ranges()[1] == (145, 155)
    from_back = ww.Groove(b.top_face, width=10, depth=20, distance=50, ref=b.back_edge)
    assert from_back.ranges()[1] == (240, 250)
    in_edge = ww.Groove(b.back_edge, width=10, depth=5)
    assert in_edge.ranges() == ((-ww.cuts.INF, ww.cuts.INF), (295, ww.cuts.INF), (-25, -15))


def test_groove_at_the_edge_is_a_rabbet() -> None:
    b = board()
    assert (
        ww.Groove(b.top_face, width=10, depth=20, distance=0).describe()
        == "rabbet 10 mm, 20 deep, in b.top_face at b.front_edge"
    )


def test_dado() -> None:
    b = board()
    dado = ww.Dado(b.top_face, width=30, depth=10, distance=100, ref=b.right_end)
    assert dado.ranges()[0] == (470, 500)
    assert cut_part(b, dado).volume == pytest.approx(600 * 300 * 40 - 30 * 300 * 10)
    assert dado.describe() == "dado 30 mm, 10 deep, in b.top_face"


def test_rabbets() -> None:
    b = board()
    rabbet = ww.Rabbet(b.top_face, at=b.back_edge, width=10, depth=20)
    assert rabbet.describe() == "rabbet 10 mm, 20 deep, in b.top_face at b.back_edge"
    end_rabbet = ww.EndRabbet(b.bottom_face, at=b.right_end, width=30, depth=10)
    assert end_rabbet.describe() == "end rabbet 30 mm, 10 deep, in b.bottom_face at b.right_end"
    volume = 600 * 300 * 40 - 600 * 10 * 20 - 30 * 300 * 10
    assert cut_part(b, rabbet, end_rabbet).volume == pytest.approx(volume)
    with pytest.raises(ValueError, match="at an end"):
        ww.EndRabbet(b.top_face, at=b.back_edge, width=10, depth=10)


def test_stopped_groove_dado_and_rabbet() -> None:
    b = board()
    groove = ww.Groove(b.top_face, width=10, depth=20, distance=50, stopped={b.right_end: 40})
    assert groove.ranges() == ((-ww.cuts.INF, 560), (50, 60), (-20, ww.cuts.INF))
    assert groove.describe() == (
        "stopped groove 10 mm, 20 deep, in b.top_face, 40 mm short of b.right_end"
    )
    dado = ww.Dado(
        b.top_face,
        width=30,
        depth=10,
        distance=100,
        stopped={b.front_edge: 15, b.back_edge: 20},
    )
    assert dado.ranges()[1] == (15, 280)
    assert dado.describe() == (
        "stopped dado 30 mm, 10 deep, in b.top_face, "
        "15 mm short of b.front_edge and 20 mm short of b.back_edge"
    )
    rabbet = ww.Rabbet(b.top_face, at=b.back_edge, width=10, depth=20, stopped={b.left_end: 40})
    assert rabbet.describe() == (
        "stopped rabbet 10 mm, 20 deep, in b.top_face at b.back_edge, 40 mm short of b.left_end"
    )
    crossing = 30 * 10 * 10  # where the dado crosses the groove
    volume = 600 * 300 * 40 - 560 * 10 * 20 - 30 * 265 * 10 - 560 * 10 * 20 + crossing
    assert cut_part(b, groove, dado, rabbet).volume == pytest.approx(volume)


def test_stops_only_where_the_cut_runs() -> None:
    b = board()
    with pytest.raises(ValueError, match="runs to"):
        ww.Groove(b.top_face, width=10, depth=20, stopped={b.front_edge: 10})
    with pytest.raises(ValueError, match="runs to"):
        ww.Dado(b.top_face, width=10, depth=10, stopped={b.left_end: 10})
    with pytest.raises(ValueError, match="within the part"):
        ww.Groove(b.top_face, width=10, depth=20, stopped={b.left_end: 600})


def test_slot_mortise() -> None:
    b = board(width=60)
    slot = ww.SlotMortise(b.left_end, width=14, depth=60)
    assert slot.ranges() == ((-ww.cuts.INF, 60), (-ww.cuts.INF, ww.cuts.INF), (-27, -13))
    assert slot.describe() == "slot mortise 14 mm, 60 deep, in b.left_end"
    with pytest.raises(ValueError, match="into an end"):
        ww.SlotMortise(b.top_face, width=14, depth=60)


def test_cuts_along_the_grain_only_into_faces_and_edges() -> None:
    b = board()
    with pytest.raises(ValueError, match="along the grain"):
        ww.Groove(b.left_end, width=10, depth=10)
    with pytest.raises(ValueError, match="across the grain"):
        ww.Dado(b.right_end, width=10, depth=10)
    with pytest.raises(ValueError, match="not adjacent"):
        ww.Rabbet(b.top_face, at=b.bottom_face, width=10, depth=10)


def test_through_mortise() -> None:
    b = board(width=60)
    mortise = ww.Mortise(b.back_edge, start=275, length=50, offset=13, width=14, depth=60)
    assert mortise.describe() == "through mortise 50 x 14 mm in b.back_edge"


def test_tongue() -> None:
    b = board(width=150)
    tongue = ww.Tongue(b.back_edge, length=10, thickness=12)
    assert tongue.describe() == "tongue 12 mm thick, 10 long, on b.back_edge"
    assert cut_part(b, tongue).volume == pytest.approx(600 * 150 * 40 + 600 * 10 * 12)
    with pytest.raises(ValueError, match="on an edge or an end"):
        ww.Tongue(b.top_face, length=10, thickness=12)


def test_one_sided_tongues_are_listed_as_rabbets() -> None:
    b = board(width=150)
    edge = ww.Tongue(b.back_edge, length=10, thickness=12, thickness_offset=0)
    assert edge.describe() == "rabbet 10 mm, 28 deep, in b.bottom_face at b.back_edge"
    end = ww.Tongue(b.left_end, length=10, thickness=12, thickness_offset=28)
    assert end.describe() == "end rabbet 10 mm, 28 deep, in b.top_face at b.left_end"
    assert cut_part(b, end).volume == pytest.approx(600 * 150 * 40 + 150 * 10 * 12)


def test_lap() -> None:
    b = board(width=60)
    lap = ww.Tenon(b.left_end, length=60, thickness=20, thickness_offset=20)
    assert lap.describe() == "lap 20 mm thick, 60 long, on b.left_end"
    assert cut_part(b, lap).volume == pytest.approx(600 * 60 * 40 + 60 * 60 * 20)


def test_chamfer() -> None:
    b = board(width=60)
    chamfer = ww.Chamfer(b.arris(b.top_face, b.back_edge), size=5, size_b=10)
    assert chamfer.describe() == "chamfer 5 x 10 mm on b.top_face_back_edge_arris"
    shape = cut_part(b, chamfer)
    assert shape.volume == pytest.approx(600 * 60 * 40 - 600 * 5 * 10 / 2)
    # 5 mm on the top face, 10 mm down the back edge.
    top = shape.faces().sort_by(bd.Axis.Z)[-1]
    assert pytest.approx(55) == top.bounding_box().max.Y
    back = shape.faces().sort_by(bd.Axis.Y)[-1]
    assert pytest.approx(-10) == back.bounding_box().max.Z


@pytest.mark.parametrize("angle", [45, 30])
def test_mitre_across_the_face(angle: float) -> None:
    b = board(width=60)
    mitre = ww.Mitre(b.right_end, inside=b.back_edge, angle=angle)
    short = 60 * math.tan(math.radians(angle))
    assert mitre.shortening == pytest.approx(short)
    shape = cut_part(b, mitre)
    assert shape.volume == pytest.approx(600 * 60 * 40 - 60 * short / 2 * 40)
    # The front edge keeps the full length, the back edge is shorter.
    assert pytest.approx(600) == shape.bounding_box().max.X
    back = shape.faces().sort_by(bd.Axis.Y)[-1]
    assert pytest.approx(600 - short) == back.bounding_box().max.X


def test_mitre_across_the_edge() -> None:
    b = board()
    mitre = ww.Mitre(b.left_end, inside=b.bottom_face)
    shape = cut_part(b, mitre)
    assert shape.volume == pytest.approx(600 * 300 * 40 - 40 * 40 / 2 * 300)
    bottom = shape.faces().sort_by(bd.Axis.Z)[0]
    assert pytest.approx(40) == bottom.bounding_box().min.X
    with pytest.raises(ValueError, match="between 0 and 90"):
        ww.Mitre(b.left_end, inside=b.bottom_face, angle=90)


def test_mitre_along_an_edge() -> None:
    b = board(width=60)
    mitre = ww.Mitre(b.back_edge, inside=b.bottom_face)
    assert mitre.shortening == pytest.approx(40)
    shape = cut_part(b, mitre)
    assert shape.volume == pytest.approx(600 * 60 * 40 - 40 * 40 / 2 * 600)
    # The top face keeps the full width, the bottom face is narrower.
    bottom = shape.faces().sort_by(bd.Axis.Z)[0]
    assert pytest.approx(20) == bottom.bounding_box().max.Y
    assert mitre.describe() == "mitre 45 deg on b.back_edge, b.bottom_face inside"
    with pytest.raises(ValueError, match=r"towards a face, not towards b\.left_end"):
        ww.Mitre(b.back_edge, inside=b.left_end)
    with pytest.raises(ValueError, match="on an end or an edge"):
        ww.Mitre(b.top_face, inside=b.back_edge)


def test_taper_over_the_whole_length() -> None:
    b = board(length=100, width=20)
    taper = ww.Taper(b.back_edge, end=b.right_end, amount=8)
    assert taper.describe() == "taper 8 mm on b.back_edge towards b.right_end"
    shape = cut_part(b, taper)
    assert shape.volume == pytest.approx(100 * 20 * 40 - 100 * 8 / 2 * 40)
    right = shape.faces().sort_by(bd.Axis.X)[-1]
    assert pytest.approx(12) == right.bounding_box().max.Y


def test_taper_over_part_of_the_length() -> None:
    b = board(length=450, width=40)
    taper = ww.Taper(b.bottom_face, end=b.left_end, amount=15, length=300)
    shape = cut_part(b, taper)
    assert shape.volume == pytest.approx(450 * 40 * 40 - 300 * 15 / 2 * 40)
    # Full thickness from 300 mm on, 15 mm thinner at the left end.
    left = shape.faces().sort_by(bd.Axis.X)[0]
    assert pytest.approx(-25) == left.bounding_box().min.Z
    assert pytest.approx(-40) == shape.bounding_box().min.Z


def test_taper_errors() -> None:
    b = board(width=20)
    with pytest.raises(ValueError, match="face or an edge"):
        ww.Taper(b.left_end, end=b.right_end, amount=5)
    with pytest.raises(ValueError, match="towards an end"):
        ww.Taper(b.back_edge, end=b.top_face, amount=5)
    with pytest.raises(ValueError, match="between 0 and 20"):
        ww.Taper(b.back_edge, end=b.right_end, amount=20)


def test_tenon_kinds() -> None:
    b = board(width=60)
    assert ww.Tenon(b.left_end, length=10, thickness=20, width=40).kind() == "tenon"
    barefaced = ww.Tenon(b.left_end, length=10, thickness=20, width=40, thickness_offset=0)
    assert barefaced.kind() == "barefaced tenon"
    whole = ww.Tenon(b.left_end, length=10, thickness=40)
    assert whole.cheeks() == 0
    assert not whole.removes_material
    assert ww.Tenon(b.left_end, length=10, thickness=40, width=50).removes_material


@pytest.mark.parametrize("half", [False, True])
def test_dovetail_tongue(half: bool) -> None:
    b = board(length=300, width=200)
    tongue = ww.DovetailTongue(b.left_end, length=7, thickness=10, slope=7, half=half)
    assert tongue.allowances() == [ww.Allowance(b.left_end, 7)]
    # 10 mm at the shoulder, wider by 1 mm (or 2 mm on both cheeks) at its end.
    wide = 11 if half else 12
    shape = cut_part(b, tongue)
    assert shape.volume == pytest.approx(300 * 200 * 40 + (10 + wide) / 2 * 7 * 200)
    end = shape.faces().sort_by(bd.Axis.X)[0]
    lo, hi = end.bounding_box().min, end.bounding_box().max
    assert (pytest.approx(-7), pytest.approx(wide)) == (lo.X, hi.Z - lo.Z)
    assert tongue.describe().startswith("half dovetail tongue" if half else "dovetail tongue")


def test_dovetail_tongue_on_a_face() -> None:
    # The whole width goes in, the edges bevelled: 96 mm at the shoulder, 100 at the end.
    b = board(length=300, width=100)
    tongue = ww.DovetailTongue(b.top_face, length=6, thickness=96, slope=3)
    assert tongue.allowances() == [ww.Allowance(b.top_face, 6)]
    shape = cut_part(b, tongue)
    assert shape.volume == pytest.approx(300 * 100 * 40 + (96 + 100) / 2 * 6 * 300)
    top = shape.faces().sort_by(bd.Axis.Z)[-1].bounding_box()
    assert (pytest.approx(6), pytest.approx(0), pytest.approx(100)) == (
        top.min.Z,
        top.min.Y,
        top.max.Y,
    )
    assert tongue.describe() == (
        "dovetail tongue 96 mm wide at the shoulder, 6 deep, 1:3, on b.top_face"
    )


def test_haunched_tenon() -> None:
    rail = ww.Board("rail", OAK, length=300, width=60)
    tenon = ww.Tenon(
        rail.left_end, length=40, thickness=8, width=40, haunch=rail.front_edge, haunch_length=10
    )
    # The haunch fills the shoulder towards the front edge, 10 mm long.
    assert tenon.haunch_boxes() == [((-10, 0), (0, 10), (-14, -6))]
    assert tenon.describe() == "haunched tenon 40 x 8 mm, 40 long, haunch 10 long, on rail.left_end"
    volume = 300 * 60 * 20 + 40 * 40 * 8 + 10 * 10 * 8
    assert cut_part(rail, tenon).volume == pytest.approx(volume)


def test_haunched_tenon_errors() -> None:
    rail = ww.Board("rail", OAK, length=300, width=60)
    with pytest.raises(ValueError, match="needs a width"):
        ww.Tenon(rail.left_end, length=40, thickness=8, haunch=rail.front_edge, haunch_length=10)
    with pytest.raises(ValueError, match=r"not to rail\.top_face"):
        ww.Tenon(
            rail.left_end, length=40, thickness=8, width=40, haunch=rail.top_face, haunch_length=10
        )
    with pytest.raises(ValueError, match="longer than the tenon"):
        ww.Tenon(
            rail.left_end,
            length=40,
            thickness=8,
            width=40,
            haunch=rail.front_edge,
            haunch_length=50,
        )


def test_tenon_with_a_mitred_end() -> None:
    rail = ww.Board("rail", OAK, length=300, width=100)
    tenon = ww.Tenon(rail.left_end, length=36, thickness=8, width=80, mitre=rail.bottom_face)
    assert tenon.describe() == (
        "tenon 80 x 8 mm, 36 long, end mitred 45 deg towards rail.bottom_face, on rail.left_end"
    )
    shape = cut_part(rail, tenon)
    # The mitre takes a triangle of 8 x 8 mm off the end of the tenon.
    assert shape.volume == pytest.approx(300 * 100 * 20 + 36 * 80 * 8 - 8 * 8 / 2 * 80)
    # The cheek towards the top face keeps the full length.
    assert pytest.approx(-36) == shape.bounding_box().min.X
    tip = [v for v in shape.vertices() if pytest.approx(-36) == v.X]
    assert {round(v.Z, 6) for v in tip} == {-6}  # the long point is an edge on the top cheek


def test_tenon_mitre_errors() -> None:
    rail = ww.Board("rail", OAK, length=300, width=100)
    with pytest.raises(ValueError, match="towards a face"):
        ww.Tenon(rail.left_end, length=36, thickness=8, width=80, mitre=rail.back_edge)
    with pytest.raises(ValueError, match="between 0 and 90"):
        ww.Tenon(
            rail.left_end, length=36, thickness=8, width=80, mitre=rail.top_face, mitre_angle=0
        )


@pytest.mark.parametrize(
    ("edges", "mitres"), [((), 0), (("back_edge",), 1), (("front_edge", "back_edge"), 2)]
)
def test_tenon_with_mitred_shoulders(edges, mitres) -> None:
    rail = ww.Board("rail", OAK, length=300, width=45)
    mitred = tuple(getattr(rail, edge) for edge in edges)
    tenon = ww.Tenon(rail.left_end, length=20, thickness=8, width=15, mitre_depth=15, mitred=mitred)
    assert tenon.allowances() == [ww.Allowance(rail.left_end, 35)]
    shape = cut_part(rail, tenon)
    # The rail reaches 15 mm beyond the shoulder, less a 15 x 15 mm triangle per mitre.
    reach = (45 * 15 - mitres * 15 * 15 / 2) * 20
    assert shape.volume == pytest.approx(300 * 45 * 20 + reach + 15 * 8 * 20)
    assert pytest.approx(-35) == shape.bounding_box().min.X


def test_mitred_shoulders_describe_and_validate() -> None:
    rail = ww.Board("rail", OAK, length=300, width=45)
    tenon = ww.Tenon(
        rail.left_end, length=20, thickness=8, width=15, mitre_depth=15, mitred=(rail.back_edge,)
    )
    assert tenon.describe() == (
        "tenon 15 x 8 mm, 20 long, reaching 15 beyond the shoulder, mitred at rail.back_edge, "
        "on rail.left_end"
    )
    with pytest.raises(ValueError, match="at an edge or an end"):
        ww.Tenon(rail.left_end, length=20, thickness=8, mitre_depth=15, mitred=(rail.top_face,))
    with pytest.raises(ValueError, match="deeper than the part is wide"):
        ww.Tenon(rail.left_end, length=20, thickness=8, mitre_depth=50, mitred=(rail.back_edge,))


def test_tenon_with_a_chamfered_end() -> None:
    rail = ww.Board("rail", OAK, length=300, width=60)
    tenon = ww.Tenon(rail.left_end, length=65, thickness=8, width=50, chamfer=3)
    assert tenon.describe() == "tenon 50 x 8 mm, 65 long, end chamfered 3 mm, on rail.left_end"
    shape = cut_part(rail, tenon)
    # Over the last 3 mm the tenon tapers from 50 x 8 to 44 x 2 mm.
    chamfers = 50 * 8 * 3 - (400 * 3 - 58 * 3**2 + 4 / 3 * 3**3)
    assert shape.volume == pytest.approx(300 * 60 * 20 + 50 * 8 * 65 - chamfers)
    end = shape & bd.Pos(-65, 0, -20) * bd.Box(1e-3, 60, 20, align=(bd.Align.MIN,) * 3)
    # The end face is 44 x 2 mm, centered on the 60 x 20 mm rail.
    box = end.bounding_box()
    assert pytest.approx((8, -11, 52, -9), abs=1e-2) == (box.min.Y, box.min.Z, box.max.Y, box.max.Z)


def test_tenon_chamfer_must_fit() -> None:
    rail = ww.Board("rail", OAK, length=300, width=60)
    with pytest.raises(ValueError, match="thinner than half"):
        ww.Tenon(rail.left_end, length=65, thickness=8, width=50, chamfer=4)
    with pytest.raises(ValueError, match="narrower than half"):
        ww.Tenon(rail.left_end, length=65, thickness=8, width=6, chamfer=3)
    with pytest.raises(ValueError, match="either mitred or chamfered"):
        ww.Tenon(rail.left_end, length=65, thickness=8, chamfer=2, mitre=rail.top_face)


def test_tenons_across_the_thickness() -> None:
    rail = ww.Board("rail", ww.Stock.board(45, "oak"), length=300, width=45)
    tenon = ww.Tenon(
        rail.left_end, length=40, thickness=10, width=30, thickness_count=2, thickness_gap=10
    )
    # Centered across the thickness as a pair, the top one first.
    assert [box[2] for box in tenon.tenon_boxes()] == [(-17.5, -7.5), (-37.5, -27.5)]
    assert tenon.describe() == (
        "2 tenons 30 x 10 mm, 40 long, 10 apart across the thickness, on rail.left_end"
    )
    assert cut_part(rail, tenon).volume == pytest.approx(300 * 45 * 45 + 2 * 30 * 10 * 40)


def test_tenons_across_the_thickness_errors() -> None:
    rail = ww.Board("rail", ww.Stock.board(45, "oak"), length=300, width=45)
    with pytest.raises(ValueError, match="need a gap"):
        ww.Tenon(rail.left_end, length=40, thickness=10, width=30, thickness_count=2)
    with pytest.raises(ValueError, match="thicker than the part"):
        ww.Tenon(
            rail.left_end, length=40, thickness=20, width=30, thickness_count=2, thickness_gap=10
        )
    with pytest.raises(ValueError, match="a tongue is a single one"):
        ww.Tongue(rail.back_edge, length=10, thickness=10, thickness_count=2, thickness_gap=10)


# --- Holes ------------------------------------------------------------------


def test_through_hole() -> None:
    board = ww.Board("b", OAK, length=300, width=60)
    hole = ww.Hole(board.top_face, 8, at={board.left_end: 20})
    assert hole.describe() == "through hole ø8, in b.top_face, 20 from b.left_end, centered"
    shape = cut_part(board, hole)
    assert 300 * 60 * 20 - shape.volume == pytest.approx(math.pi * 4**2 * 20)
    design_box = bd.Box(300, 60, 20, align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MAX))
    lo, hi = bbox(hole.removal() & design_box)
    assert lo == (16, 26, -20)
    assert hi == (24, 34, 0)


def test_blind_hole_in_an_edge_with_a_drill_point() -> None:
    board = ww.Board("b", OAK, length=300, width=60)
    hole = ww.Hole(board.back_edge, 8, depth=30, at={board.right_end: 50}, point=118)
    assert hole.describe() == (
        "hole ø8, 30 deep, drill point 118 deg, in b.back_edge, 50 from b.right_end, centered"
    )
    point = 4 / math.tan(math.radians(59))
    removed = 300 * 60 * 20 - cut_part(board, hole).volume
    assert removed == pytest.approx(math.pi * 16 * (30 + point / 3))
    assert tuple(hole.center()) == pytest.approx((250, 60, -10))


def test_counterbored_and_countersunk_holes() -> None:
    board = ww.Board("b", OAK, length=300, width=60)
    bored = ww.Hole(board.top_face, 5, at={board.left_end: 30}, counterbore=10, counterbore_depth=8)
    sunk = ww.Hole(board.top_face, 5, at={board.right_end: 30}, countersink=10)
    assert "counterbored ø10, 8 deep" in bored.describe()
    assert "countersunk ø10, 90 deg" in sunk.describe()
    assert sunk.countersink_depth == pytest.approx(2.5)
    removed = 300 * 60 * 20 - cut_part(board, bored, sunk).volume
    cone = math.pi * 2.5 / 3 * (5**2 + 5 * 2.5 + 2.5**2) - math.pi * 2.5**2 * 2.5
    expected = 2 * math.pi * 2.5**2 * 20 + math.pi * (5**2 - 2.5**2) * 8 + cone
    assert removed == pytest.approx(expected)


def test_tapered_holes() -> None:
    board = ww.Board("seat", ww.Stock.board(40, "elm"), length=400, width=400)
    blind = ww.Hole(board.bottom_face, 20, depth=30, bottom_diameter=16, at={board.left_end: 100})
    through = ww.Hole(board.bottom_face, 24, bottom_diameter=18, at={board.right_end: 100})
    assert blind.describe().startswith("tapered hole ø20 to ø16, 30 deep, in seat.bottom_face")
    assert through.describe().startswith("through tapered hole ø24 to ø18, in seat.bottom_face")

    def frustum(r1: float, r2: float, h: float) -> float:
        return math.pi * h / 3 * (r1 * r1 + r1 * r2 + r2 * r2)

    removed = 400 * 400 * 40 - cut_part(board, blind, through).volume
    assert removed == pytest.approx(frustum(10, 8, 30) + frustum(12, 9, 40))


def test_hole_must_fit() -> None:
    board = ww.Board("b", OAK, length=300, width=60)
    with pytest.raises(ValueError, match="doesn't fit"):
        ww.Hole(board.top_face, 10, at={board.left_end: 4})
    with pytest.raises(ValueError, match="within 20 mm"):
        ww.Hole(board.top_face, 10, depth=25)
    with pytest.raises(ValueError, match="not adjacent"):
        ww.Hole(board.top_face, 10, at={board.bottom_face: 4})
    with pytest.raises(ValueError, match="either counterbored or countersunk"):
        ww.Hole(board.top_face, 5, counterbore=10, counterbore_depth=2, countersink=10)
    with pytest.raises(ValueError, match="no drill point"):
        ww.Hole(board.top_face, 5, point=118)


def test_holes_in_a_rod() -> None:
    rod = ww.Rod("dowel", ww.Stock.rod(20, "beech"), length=100)
    end = ww.Hole(rod.right_end, 6, depth=30)
    cross = ww.Hole(rod.top_face, 6, at={rod.left_end: 20})
    assert end.describe() == "hole ø6, 30 deep, in dowel.right_end, centered"
    assert tuple(end.center()) == pytest.approx((100, 10, -10))
    assert tuple(cross.center()) == pytest.approx((20, 10, 0))
    shape = cut_part(rod, end)
    assert shape.volume == pytest.approx(math.pi * (100 * 100 - 9 * 30))
    with pytest.raises(ValueError, match="within the end of dowel"):
        ww.Hole(rod.left_end, 6, depth=10, at={rod.front_edge: 2})


# --- Rods -------------------------------------------------------------------


def test_end_chamfers() -> None:
    rod = ww.Rod("dowel", ww.Stock.rod(10, "beech"), length=40)
    chamfer = ww.EndChamfer(rod.right_end, 1)
    assert chamfer.describe() == "chamfer 1 mm around dowel.right_end"
    # A ring of triangular section, 1 x 1, at radius 4 to 5 (Pappus).
    ring = 0.5 * 2 * math.pi * (5 - 1 / 3)
    assert cut_part(rod, chamfer).volume == pytest.approx(math.pi * 25 * 40 - ring)

    leg = ww.Board("leg", ww.Stock.board(40, "oak"), length=400, width=40)
    foot = ww.EndChamfer(leg.left_end, 3, length=6)
    assert foot.describe() == "chamfer 3 x 6 mm around leg.left_end"
    # Four chamfers, minus the overlaps at the corners counted twice.
    removed = 4 * 40 * 3 * 6 / 2 - 4 * 3 * 3 * 6 / 3
    assert cut_part(leg, foot).volume == pytest.approx(400 * 40 * 40 - removed)


def test_round_taper_and_point() -> None:
    rod = ww.Rod("leg", ww.Stock.rod(40, "oak"), length=450)
    taper = ww.RoundTaper(rod.left_end, 28, length=300)
    assert taper.describe() == "round taper to ø28 over 300 mm towards leg.left_end"
    frustum = math.pi * 300 / 3 * (20**2 + 20 * 14 + 14**2)
    assert cut_part(rod, taper).volume == pytest.approx(math.pi * 400 * 150 + frustum)

    peg = ww.Rod("peg", ww.Stock.rod(10, "oak"), length=60)
    point = ww.RoundTaper(peg.right_end, 0, length=15)
    assert point.describe() == "point over 15 mm on peg.right_end"
    assert cut_part(peg, point).volume == pytest.approx(math.pi * 25 * (45 + 15 / 3))

    board = ww.Board("b", OAK, length=300, width=60)
    with pytest.raises(ValueError, match="turned on a rod"):
        ww.RoundTaper(board.left_end, 10)
    with pytest.raises(ValueError, match="under ø10"):
        ww.RoundTaper(peg.left_end, 12)


def test_flat_on_a_rod() -> None:
    rod = ww.Rod("half_dowel", ww.Stock.rod(20, "oak"), length=100)
    flat = ww.Flat(rod.bottom_face, 10)
    assert flat.describe() == "flat 20 mm wide, 10 deep, on half_dowel.bottom_face"
    assert cut_part(rod, flat).volume == pytest.approx(math.pi * 100 * 100 / 2)
    assert ww.Flat(rod.top_face, 2).width == pytest.approx(12)
    with pytest.raises(ValueError, match="along a rod"):
        ww.Flat(rod.left_end, 2)


def test_rods_refuse_cuts_needing_planar_sides() -> None:
    rod = ww.Rod("rung", ww.Stock.rod(25, "oak"), length=300)
    with pytest.raises(ValueError, match="a groove needs a board, rung is a rod"):
        ww.Groove(rod.top_face, width=5, depth=5)
    with pytest.raises(ValueError, match="needs a board"):
        ww.Chamfer(rod.arris(rod.left_end, rod.top_face), size=2)
    with pytest.raises(ValueError, match="needs a board"):
        ww.Tenon(rod.left_end, length=20, thickness=8)
    with pytest.raises(ValueError, match="mitred at its ends"):
        ww.Mitre(rod.back_edge, inside=rod.top_face)


def test_planar_cuts_on_a_rod() -> None:
    rod = ww.Rod("rung", ww.Stock.rod(20, "oak"), length=300)
    taper = ww.Taper(rod.top_face, end=rod.right_end, amount=10, length=100)
    mitre = ww.Mitre(rod.left_end, inside=rod.back_edge)
    assert taper.describe() == "flat taper 10 mm over 100 on rung.top_face towards rung.right_end"
    shape = cut_part(rod, taper, mitre)
    # The mitre takes half a cylinder 20 long. The taper takes a segment of
    # the section, growing to a half disc: its area integrated over the depth
    # is that of the half disc weighted by the height above the axis, 2 r^3 / 3.
    removed = math.pi * 100 * 20 / 2 + 100 / 10 * 2 * 10**3 / 3
    assert shape.volume == pytest.approx(math.pi * 100 * 300 - removed)
