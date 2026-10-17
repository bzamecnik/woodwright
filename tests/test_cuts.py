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


def test_dovetail_tongue_not_on_a_face() -> None:
    b = board()
    with pytest.raises(ValueError, match="end or an edge"):
        ww.DovetailTongue(b.top_face, length=7, thickness=10)


def test_haunched_tenon() -> None:
    rail = ww.Board("rail", OAK, length=300, width=60)
    tenon = ww.Tenon(
        rail.left_end, length=40, thickness=8, width=40, haunch=rail.front_edge, haunch_length=10
    )
    # The haunch fills the shoulder towards the front edge, 10 mm long.
    assert tenon.haunch_box() == ((-10, 0), (0, 10), (-14, -6))
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
