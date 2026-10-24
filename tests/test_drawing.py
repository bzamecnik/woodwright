from pathlib import Path

import pytest

import woodwright as ww
from woodwright.drawing import (
    Row,
    Side,
    _assign,
    _clip,
    _ranges,
    _stagger,
    assembly_sheet,
    features,
    part_sheet,
    parts_sheet,
)
from woodwright.examples import get
from woodwright.export import export_model

OAK = ww.Stock.board(20, "oak")
BOARD_ORDER = [
    Side.TOP_FACE,
    Side.FRONT_EDGE,
    Side.RIGHT_END,
    Side.LEFT_END,
    Side.BOTTOM_FACE,
    Side.BACK_EDGE,
]
BOARD_DEFAULTS = [Side.TOP_FACE, Side.FRONT_EDGE]


def _positions(feature, axis: int) -> list[float]:
    return sorted({round(v, 2) for a, v, _ in feature.coords if a == axis})


def _resolved(name: str, part: str):
    model = get(name)().resolve()
    return model, next(p for p in model.parts if p.part.name == part)


def test_a_mortise_is_dimensioned_on_the_edge_it_is_cut_into() -> None:
    _, stile = _resolved("joints.mortise_tenon", "stile")
    (mortise,) = features(stile)

    assert mortise.opens == [Side.BACK_EDGE]
    assert _positions(mortise, 0) == [275, 325]  # its ends
    assert _positions(mortise, 1) == [18]  # its bottom, 42 deep
    assert _positions(mortise, 2) == [-14, -6]  # its cheeks

    chosen = _assign([mortise], BOARD_ORDER, BOARD_DEFAULTS)
    assert set(chosen) == {
        (Side.BACK_EDGE, 0),
        (Side.BACK_EDGE, 2),
        (Side.TOP_FACE, 1),  # the depth, to hidden lines
    }


def test_a_tenon_shows_its_cheeks_on_its_end_and_its_shoulder_on_the_face() -> None:
    _, rail = _resolved("joints.mortise_tenon", "rail")
    (tenon,) = features(rail)

    assert tenon.opens[0] == Side.LEFT_END
    assert _positions(tenon, 0) == [0]  # the shoulder, 40 from the end of the blank
    assert _positions(tenon, 1) == [5, 55]
    assert _positions(tenon, 2) == [-14, -6]

    chosen = _assign([tenon], BOARD_ORDER, BOARD_DEFAULTS)
    assert set(chosen) == {(Side.TOP_FACE, 0), (Side.LEFT_END, 1), (Side.LEFT_END, 2)}


def test_dovetails_are_dimensioned_where_they_are_marked_out() -> None:
    _, top = _resolved("joints.dovetail_corner", "top")
    (tails,) = features(top)

    # on the face (the slope shows there), at the end of the board only
    chosen = _assign([tails], BOARD_ORDER, BOARD_DEFAULTS)
    (shown,) = chosen[(Side.TOP_FACE, 1)]
    assert _positions(shown, 1) == [10, 49, 57, 96, 104, 143, 151, 190]
    assert _positions(tails, 0) == [0]  # the baseline


def test_holes_are_dimensioned_by_their_centres() -> None:
    board = ww.Board("board", OAK, length=300, width=100)
    board.cut(ww.Hole(board.top_face, 20, at={board.left_end: 80}))
    asm = ww.Assembly("hole")
    asm.add(board)
    (hole,) = features(asm.resolve()[board])

    assert _positions(hole, 0) == [80]
    assert _positions(hole, 1) == [50]
    assert _positions(hole, 2) == []  # through
    ((axis, centre, radius),) = hole.holes
    assert (axis, radius) == (2, pytest.approx(10))
    assert centre[:2] == pytest.approx((80, 50))


def test_text_that_does_not_fit_is_staggered() -> None:
    texts = _stagger(Row([0, 2, 4, 100]), scale=1)
    assert [level for _, level, _ in texts] == [0, 1, 0]
    # beside the ticks at the end of a row
    ((text, level, centre),) = _stagger(Row([0, 2]), scale=1)
    assert (text, level) == ("2", 0) and centre > 2


def test_part_sheet() -> None:
    model, rail = _resolved("joints.mortise_tenon", "rail")
    svg = part_sheet(model, rail).svg()

    assert svg.startswith("<svg") and 'width="297.0mm"' in svg  # A4 landscape
    for text in ("TOP FACE", "LEFT END", "340", "300", "tenon 50 x 8 mm", "1:2, mm"):
        assert f">{text}" in svg or text in svg


def test_assembly_and_parts_sheets() -> None:
    model = get("projects.drawer")().resolve()
    assembly = assembly_sheet(model).svg()
    parts = parts_sheet(model).svg()

    assert "FRONT" in assembly and "RIGHT SIDE" in assembly and "ISOMETRIC" in assembly
    assert "EXPLODED" in parts
    for group in model.groups:
        assert f">{group.name}<" in parts
    assert ">left_right<" in parts and ">1 mirror image<" in parts


def test_export_writes_drawings(tmp_path: Path) -> None:
    model = get("joints.mortise_tenon")().resolve()
    export_model(model, tmp_path)
    drawings = sorted(p.name for p in (tmp_path / "drawings").iterdir())
    assert drawings == ["assembly.svg", "parts.svg", "rail.svg", "stile.svg"]
    assert (tmp_path / "plans.pdf").read_bytes().count(b"/Type /Page\n") == 4


def test_identical_parts_share_a_sheet(tmp_path: Path) -> None:
    model = get("projects.stool")().resolve()
    export_model(model, tmp_path)
    drawings = sorted(p.name for p in (tmp_path / "drawings").iterdir())
    assert drawings == [
        "assembly.svg",
        "leg.svg",
        "parts.svg",
        "seat.svg",
        "stretcher_front_back.svg",
        "stretcher_right_left.svg",
        "wedge.svg",
    ]
    leg = (tmp_path / "drawings" / "leg.svg").read_text()
    assert ">4 (2 mirror image)<" in leg
    assert "4 pieces: leg_front_left, leg_back_right; mirror image:" in leg


@pytest.mark.parametrize("name", ["cuts.dowel", "joints.butterfly_joint", "projects.coat_rack"])
def test_sheets_of_other_parts(name: str) -> None:
    model = get(name)().resolve()
    for part in model.parts:
        assert "<svg" in part_sheet(model, part).svg()


def test_crowded_features_are_shown_in_details() -> None:
    model, rail = _resolved("projects.chair", "back_rail_lower")
    svg = part_sheet(model, rail).svg()

    # the mortises across the thin back edge, enlarged, all three (identical,
    # numbered alike) in one detail
    assert ">BACK EDGE: 3  1:1<" in svg
    assert ">3  3 x mortise 20 x 8 mm, 22 deep, in back_edge<" in svg
    assert ">LEFT END  1:2<" in svg  # the ends at their own scale
    assert "1:4, mm" in svg  # the sheet's scale


def test_identical_features_share_a_number() -> None:
    model = get("cuts.shelf_pin_holes")().resolve()
    svg = part_sheet(model, model.parts[0]).svg()
    assert ">1  24 x hole ø5, 12 deep, drill point 118 deg, in top_face<" in svg
    # one balloon on the top face (on a leader to one of them) and one in the
    # detail of the front edge, and "make 1"
    assert svg.count(">1</text>") == 3
    assert ">2</text>" not in svg


def test_a_rabbet_is_detailed_in_one_view() -> None:
    model, bottom = _resolved("projects.drawer", "bottom")
    svg = part_sheet(model, bottom).svg()

    # width and depth of each rabbet together, one detail each
    assert svg.count(": 1  2:1<") == svg.count(": 2  2:1<") == svg.count(": 3  2:1<") == 1


def test_chamfers_are_called_out_not_dimensioned() -> None:
    _, leg = _resolved("projects.chair", "leg_back_left")
    chamfers = [f for f in features(leg) if f.text.startswith("chamfer")]
    assert chamfers and all(not f.coords for f in chamfers)


def test_clip_and_ranges() -> None:
    pieces = _clip([(-10, 5), (5, 5), (5, 20)], ((0, 0), (10, 10)))
    assert pieces == [[(0, 5), (5, 5), (5, 10)]]
    assert _ranges([1, 3, 4, 5, 9, 10]) == "1, 3-5, 9, 10"
