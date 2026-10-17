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
            assert overlap is None or overlap.volume < 1e-6, f"{a.label} and {b.label} interfere"


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
