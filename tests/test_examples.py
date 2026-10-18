from pathlib import Path

import pytest

from woodwright.examples import ALL, frames, name
from woodwright.examples.__main__ import main


@pytest.mark.parametrize("example", ALL, ids=name)
def test_example_resolves_without_interference(example) -> None:
    model = example().resolve()
    model.compound()
    shapes = [part.placed_shape for part in model.parts]
    for i, a in enumerate(shapes):
        for b in shapes[i + 1 :]:
            overlap = a.intersect(b)
            assert _volume(overlap) < 1e-6, f"{a.label} and {b.label} interfere"


def test_cli_lists_and_exports(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list"]) == 0
    assert "frames.mortise_tenon_frame" in capsys.readouterr().out

    assert main(["export", "joints.mortise_tenon", "--out", str(tmp_path), "--no-views"]) == 0
    out_dir = tmp_path / "joints" / "mortise_tenon"
    assert sorted(p.name for p in out_dir.iterdir()) == [
        "assembled.step",
        "assembled.stl",
        "cut_list.txt",
        "rail.stl",
        "stile.stl",
    ]
    assert "mortise 50 x 8 mm" in (out_dir / "cut_list.txt").read_text()


def test_cli_rejects_unknown_examples() -> None:
    with pytest.raises(SystemExit):
        main(["export", "joints.nope"])


def test_frame_and_panel_sizes() -> None:
    model = frames.frame_and_panel().resolve()
    sizes = {part.part.name: part.size for part in model.parts}
    assert sizes["panel"] == (500, 320, 10)  # the opening plus the grooves
    assert sizes["rail_top"] == (380, 60, 20)  # shoulder to shoulder plus the tenons


def test_frame_and_panel_fills_the_grooves() -> None:
    import build123d as bd

    model = frames.frame_and_panel().resolve()
    parts = {part.part.name: part for part in model.parts}
    stile = parts["stile_left"]
    groove = next(cut for cut in stile.cuts if cut.describe().startswith("groove"))
    design_box = bd.Box(600, 60, 20, align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MAX))
    region = stile.location * (groove.removal() & design_box)
    filled = sum(
        (region & parts[name].placed_shape).volume for name in ("rail_top", "rail_bottom", "panel")
    )
    # The haunches, the tenons and the panel fill the groove running through the stile.
    assert filled == pytest.approx(region.volume)


def _volume(shape) -> float:
    """Volume of an intersection: nothing, one shape or a list of them."""
    if shape is None:
        return 0.0
    return sum(s.volume for s in shape) if isinstance(shape, list) else shape.volume


def test_drawer_sizes_and_bottom() -> None:
    from woodwright.examples import projects

    model = projects.drawer().resolve()
    sizes = {part.part.name: part.size for part in model.parts}
    assert sizes["front"] == (400, 150, 20)  # the overall width
    assert sizes["left"] == (445, 150, 12)  # the tails reach 15 into the front
    assert sizes["back"] == (400, 134, 12)  # sits on the bottom
    assert sizes["bottom"] == (386, 435, 10)  # in the grooves, under the back
    box = model.compound().bounding_box()
    assert tuple(box.size) == pytest.approx((400, 450, 150))


def test_table_top_and_buttons() -> None:
    import build123d as bd

    import woodwright as ww
    from woodwright.examples import projects

    model = projects.table().resolve()
    box = model.compound().bounding_box()
    assert tuple(box.min) == pytest.approx((-40, -40, 0))  # the top overhangs the legs
    assert tuple(box.size) == pytest.approx((1280, 830, 750))
    parts = {part.part.name: part for part in model.parts}
    # Each button's tongue reaches 4 mm into its mortise and its top touches the top.
    for button, apron in [("button_front_2", "apron_front"), ("button_left_1", "apron_left")]:
        board = parts[apron].part
        design_box = bd.Pos(0, 0, -board.thickness) * bd.Box(
            board.length, board.width, board.thickness, align=(bd.Align.MIN,) * 3
        )
        mortises = [
            cut.removal() & design_box for cut in parts[apron].cuts if isinstance(cut, ww.Pocket)
        ]
        placed = parts[button].placed_shape
        tongue = sum((placed & (parts[apron].location * m)).volume for m in mortises)
        assert tongue == pytest.approx(4 * 6 * 40)
        assert pytest.approx(720) == placed.bounding_box().max.Z


def test_drawer_groove_is_hidden_in_the_tails() -> None:
    import build123d as bd

    from woodwright.examples import projects

    model = projects.drawer().resolve()
    front = next(part for part in model.parts if part.part.name == "front")
    # The front's ends beyond the sides' inside faces hold only the pins; the
    # groove running out of the front doesn't cut them.
    sockets = [cut for cut in front.cuts if cut.describe().startswith("sockets")]
    for x0 in (-12, front.part.length):
        end = bd.Pos(x0, 0, -20) * bd.Box(12, 150, 20, align=(bd.Align.MIN,) * 3)
        pins = end
        for cut in sockets:
            pins -= cut.removal()
        assert (front.shape & end).volume == pytest.approx(pins.volume)


def test_chair_sizes_and_through_tenons() -> None:
    import build123d as bd

    from woodwright.examples import projects

    model = projects.chair().resolve()
    box = model.compound().bounding_box()
    # The through tenons stand 2 mm proud of the legs on all sides,
    # and the seat overhangs the frame by 10 mm at the front and the sides.
    assert tuple(box.min) == pytest.approx((-10, -10, 0))
    assert tuple(box.size) == pytest.approx((460, 432, 900))
    parts = {part.part.name: part for part in model.parts}
    assert parts["leg_front_left"].size == (430, 40, 40)
    assert parts["leg_back_left"].size == (900, 40, 40)
    assert pytest.approx(430) == parts["seat_rail_back"].placed_shape.bounding_box().max.Z
    for board in ("seat_1", "seat_2"):
        assert parts[board].size == (460, 215, 20)
        seat_box = parts[board].placed_shape.bounding_box()
        assert pytest.approx((430, 450)) == (seat_box.min.Z, seat_box.max.Z)
    # The back board is notched at the corners around the legs, 50 x 40 mm each.
    notches = parts["seat_1"].placed_shape.volume - parts["seat_2"].placed_shape.volume
    assert notches == pytest.approx(2 * 50 * 40 * 20, rel=0.02)
    # Three splats between the back rails, their tenons 20 mm into them.
    splats = [part for key, part in parts.items() if key.startswith("splat")]
    assert len(splats) == 3
    for splat in splats:
        splat_box = splat.placed_shape.bounding_box()
        assert pytest.approx((600, 830)) == (splat_box.min.Z, splat_box.max.Z)
    # The legs are 35 mm square at the floor.
    leg = parts["leg_front_left"].placed_shape
    foot = leg & bd.Box(100, 100, 0.01, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    assert pytest.approx((35, 35), abs=0.01) == tuple(foot.bounding_box().size)[:2]


def test_stepstool_seat_battens_housed_in_both_boards() -> None:
    from woodwright.examples import projects

    model = projects.stepstool_seat().resolve()
    box = model.compound().bounding_box()
    assert tuple(box.size) == pytest.approx((400, 280, 40))
    parts = {part.part.name: part for part in model.parts}
    # Lying flat, the whole width goes into the housing, its edges bevelled.
    assert parts["batten_left"].size == (280, 90, 26.5)
    assert [cut.describe() for cut in parts["batten_left"].cuts] == [
        "dovetail tongue 86.75 mm wide at the shoulder, 6.5 deep, 1:4, on batten_left.top_face"
    ]
    for board in ("seat_1", "seat_2"):
        sockets = [cut.describe() for cut in parts[board].cuts]
        assert (
            sockets
            == [f"dovetail socket 86.75 mm at the face, 6.5 deep, 1:4, in {board}.bottom_face"] * 2
        )
    batten_box = parts["batten_left"].placed_shape.bounding_box()
    assert tuple(batten_box.min) == pytest.approx((30, 0, -40))
    # Each batten's one tongue fills the housings in both boards.
    total = sum(part.shape.volume for part in model.parts)
    assert total == pytest.approx(2 * 400 * 140 * 20 + 2 * 280 * 90 * 20)


def test_ledged_door_tongues_fill_the_grooves() -> None:
    from woodwright.examples import projects

    model = projects.ledged_door().resolve()
    box = model.compound().bounding_box()
    assert tuple(box.size) == pytest.approx((400, 40, 600))  # the ledges behind the boards
    sizes = {part.part.name: part.size for part in model.parts}
    assert sizes["board_1"] == (600, 100, 20)  # the first board has no tongue
    assert sizes["board_2"] == (600, 110, 20)
    assert sizes["ledge_top"] == (370, 80, 20)
    # The tongues fill the grooves; only the V-chamfers along the joints are gone.
    boards = sum(part.shape.volume for part in model.parts if part.part.name.startswith("board"))
    assert boards == pytest.approx(400 * 600 * 20 - 6 * 3 * 3 / 2 * 600)


def test_butt_frame_and_panel_tongues() -> None:
    model = frames.butt_frame_and_panel().resolve()
    box = model.compound().bounding_box()
    assert tuple(box.size) == pytest.approx((420, 20, 500))
    parts = {part.part.name: part for part in model.parts}
    assert parts["rail_top"].size == (300, 60, 20)  # butted, no tenons
    assert parts["panel"].size == (400, 320, 10)  # the opening plus the tongues
    # The tongue runs all round, its corners too, into the grooves in the stiles.
    tongues = (2 * 380 + 2 * 300) * 10 * 6 + 4 * 10 * 10 * 6
    assert parts["panel"].shape.volume == pytest.approx(380 * 300 * 10 + tongues)
    for stile, edge in [("stile_left", "back_edge"), ("stile_right", "front_edge")]:
        cuts = [cut.describe() for cut in parts[stile].cuts]
        assert cuts == [f"groove 6 mm, 10 deep, in {stile}.{edge}"]  # through


def test_shiplap_panel_laps_fill_the_rabbets() -> None:
    from woodwright.examples import joints

    model = joints.shiplap_panel().resolve()
    box = model.compound().bounding_box()
    assert tuple(box.size) == pytest.approx((500, 450, 20))  # flat, the visible widths
    parts = {part.part.name: part for part in model.parts}
    assert parts["board_2"].size == (500, 162, 20)  # with the lap
    assert [cut.describe() for cut in parts["board_2"].cuts] == [
        "rabbet 12 mm, 10 deep, in board_2.bottom_face at board_2.front_edge",
        "rabbet 10 mm, 12 deep, in board_2.back_edge at board_2.top_face",
    ]
    total = sum(part.shape.volume for part in model.parts)
    assert total == pytest.approx(3 * 500 * 150 * 20)


def test_haunched_tenon_has_a_small_inner_shoulder() -> None:
    from woodwright.examples import joints

    model = joints.haunched_mortise_tenon_corner().resolve()
    parts = {part.part.name: part for part in model.parts}
    assert parts["rail"].size == (225, 60, 20)  # as long as the stub tenon
    # 10 mm shoulders on both edges, the outer one filled by the haunch.
    cuts = [cut.describe() for cut in parts["rail"].cuts]
    assert cuts[-1] == "haunched tenon 40 x 8 mm, 25 long, haunch 10 long, on rail.left_end"
    stile_cuts = [cut.describe() for cut in parts["stile"].cuts]
    assert stile_cuts[1:] == [
        "mortise 40 x 8 mm, 27 deep, in stile.back_edge",
        "haunch mortise 10 x 8 mm, 10 deep, in stile.back_edge at stile.right_end",
    ]


def test_haunched_stub_tenon_fills_the_groove_at_the_end() -> None:
    import build123d as bd

    from woodwright.examples import joints

    model = joints.haunched_stub_tenon_corner().resolve()
    parts = {part.part.name: part for part in model.parts}
    assert parts["rail"].size == (225, 60, 20)  # the stub tenon is 25 long
    cuts = [cut.describe() for cut in parts["rail"].cuts]
    assert cuts[-1] == "haunched tenon 30 x 8 mm, 25 long, haunch 10 long, on rail.left_end"
    # Between the end of the stile and the tenon the haunch fills the groove.
    stile = parts["stile"]
    groove_end = bd.Pos(280, 50, -14) * bd.Box(20, 10, 8, align=(bd.Align.MIN,) * 3)
    haunch = parts["rail"].placed_shape & (stile.location * groove_end)
    assert haunch.volume == pytest.approx(20 * 10 * 8)


def test_side_table_sizes_and_stretchers() -> None:
    import build123d as bd

    from woodwright.examples import projects

    model = projects.side_table().resolve()
    box = model.compound().bounding_box()
    assert tuple(box.min) == pytest.approx((-25, -25, 0))  # the top overhangs the legs
    assert tuple(box.size) == pytest.approx((450, 450, 550))
    parts = {part.part.name: part for part in model.parts}
    assert parts["leg_front_left"].size == (530, 40, 40)
    # All at the same level, their blind tenons mitred, meeting on the legs' diagonals.
    assert parts["stretcher_front"].size == (368, 30, 20)
    for side in ("front", "right", "back", "left"):
        stretcher_box = parts[f"stretcher_{side}"].placed_shape.bounding_box()
        assert pytest.approx((120, 150)) == (stretcher_box.min.Z, stretcher_box.max.Z)
    leg = bd.Box(40, 40, 550, align=(bd.Align.MIN,) * 3)
    front = parts["stretcher_front"].placed_shape & leg
    left = parts["stretcher_left"].placed_shape & leg
    assert front.volume == pytest.approx(20 * 8 * (24 + 16) / 2)
    assert front.distance_to(left) == pytest.approx(0)
    for board in ("top_1", "top_2", "top_3"):
        top_box = parts[board].placed_shape.bounding_box()
        assert pytest.approx((530, 550)) == (top_box.min.Z, top_box.max.Z)
    assert sum(key.startswith("button") for key in parts) == 8
