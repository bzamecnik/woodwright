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
    from woodwright.examples import projects

    model = projects.chair().resolve()
    box = model.compound().bounding_box()
    # The through tenons stand 2 mm proud of the legs on all sides.
    assert tuple(box.min) == pytest.approx((-2, -2, 0))
    assert tuple(box.size) == pytest.approx((444, 424, 900))
    parts = {part.part.name: part for part in model.parts}
    assert parts["leg_front_left"].size == (450, 40, 40)
    assert parts["leg_back_left"].size == (900, 40, 40)
    assert pytest.approx(450) == parts["seat_rail_back"].placed_shape.bounding_box().max.Z
    assert pytest.approx(870) == parts["back_rail_upper"].placed_shape.bounding_box().max.Z
