"""Grouping identical parts and mirror pairs."""

import woodwright as ww
from woodwright.examples import projects
from woodwright.grouping import _group_names, group_name

OAK = ww.Stock.board(20, "oak")


def groups(asm: ww.Assembly) -> list[tuple[str, list[str], list[str]]]:
    return [
        (g.name, [p.part.name for p in g.parts], [p.part.name for p in g.mirrored])
        for g in asm.resolve().groups
    ]


def test_table_legs_and_buttons_are_identical() -> None:
    found = {name: (parts, mirrored) for name, parts, mirrored in groups(projects.table())}
    legs, mirrored = found["leg"]
    assert legs == ["leg_front_left", "leg_front_right", "leg_back_right", "leg_back_left"]
    assert mirrored == []
    assert len(found["button"][0]) == 10
    assert found["apron_front_back"][0] == ["apron_front", "apron_back"]
    assert found["apron_right_left"][0] == ["apron_right", "apron_left"]


def test_drawer_sides_are_a_mirror_pair() -> None:
    found = groups(projects.drawer())
    assert ("left_right", ["left", "right"], ["right"]) in found
    assert ("front", ["front"], []) in found


def test_round_legs_drilled_the_other_way_round_are_mirror_images() -> None:
    found = {name: (parts, mirrored) for name, parts, mirrored in groups(projects.stool())}
    legs, mirrored = found["leg"]
    assert len(legs) == 4
    assert mirrored == ["leg_front_right", "leg_back_left"]


def test_a_part_turned_end_for_end_is_identical() -> None:
    asm = ww.Assembly("pair")
    a = asm.add(ww.Board("rail_a", OAK, length=300, width=60))
    b = asm.add(ww.Board("rail_b", OAK, length=300, width=60))
    a.cut(ww.Dado(a.top_face, width=20, depth=5, distance=50))
    b.cut(ww.Dado(b.bottom_face, width=20, depth=5, distance=230))
    asm.join(ww.Butt(a.back_edge, b.front_edge))
    assert groups(asm) == [("rail", ["rail_a", "rail_b"], [])]


def test_a_part_cut_differently_is_not_identical() -> None:
    asm = ww.Assembly("pair")
    a = asm.add(ww.Board("rail_a", OAK, length=300, width=60))
    b = asm.add(ww.Board("rail_b", OAK, length=300, width=60))
    a.cut(ww.Dado(a.top_face, width=20, depth=5, distance=50))
    b.cut(ww.Dado(b.top_face, width=20, depth=5, distance=60))
    asm.join(ww.Butt(a.back_edge, b.front_edge))
    assert [parts for _, parts, _ in groups(asm)] == [["rail_a"], ["rail_b"]]


def test_other_stock_is_not_identical() -> None:
    asm = ww.Assembly("pair")
    a = asm.add(ww.Board("a", OAK, length=300, width=60))
    b = asm.add(ww.Board("b", ww.Stock.board(20, "walnut"), length=300, width=60))
    asm.join(ww.Butt(a.back_edge, b.front_edge))
    assert len(groups(asm)) == 2


def test_group_names() -> None:
    assert group_name(["leg_front_left", "leg_back_right"]) == "leg"
    assert group_name(["left_front_leg", "right_back_leg"]) == "leg"
    assert group_name(["top_beam_1", "top_beam_2"]) == "top_beam"
    assert group_name(["left", "right"]) == "left_right"
    assert group_name(["a", "b", "c", "d"]) == "a"
    assert group_name(["top_2"]) == "top_2"
    # groups that would share a name, or take a part's name, tell their parts apart
    assert _group_names([["top_1", "top_4"], ["top_2", "top_3"]]) == ["top_1_4", "top_2_3"]
    assert _group_names([["top"], ["top_1", "top_2"]]) == ["top", "top_1_2"]
