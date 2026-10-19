from pathlib import Path

import pytest

from woodwright.cli import load_designs, main

DESIGN = """
import woodwright as ww
from woodwright.examples import joints

door = joints.mortise_tenon(rail_length=200)
_hidden = joints.mortise_tenon()


def corner(length: float = 300) -> ww.Assembly:
    asm = ww.Assembly("corner")
    oak = ww.Stock.board(thickness=20, species="oak")
    stile = asm.add(ww.Board("stile", oak, length=length, width=60))
    rail = asm.add(ww.Board("rail", oak, length=200, width=60))
    asm.join(ww.MortiseTenon(tenon=rail.left_end, mortise=stile.back_edge))
    return asm


def needs_arguments(length: float) -> ww.Assembly:
    return corner(length)


if __name__ == "__main__":
    raise SystemExit("not run on export")
"""


@pytest.fixture
def design(tmp_path: Path) -> Path:
    path = tmp_path / "my_design.py"
    path.write_text(DESIGN)
    return path


def test_loads_variables_and_functions_returning_assemblies(design: Path) -> None:
    designs = load_designs(design)
    assert list(designs) == ["door", "corner"]
    assert designs["corner"]().name == "corner"


def test_exports_a_design_file(design: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    assert main(["export", str(design), "--out", str(out), "--no-views"]) == 0
    assert sorted(p.name for p in (out / "my_design").iterdir()) == ["corner", "door"]
    cut_list = (out / "my_design" / "door" / "cut_list.txt").read_text()
    assert "rail" in cut_list


def test_exports_one_named_design(design: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    assert main(["export", f"{design}:corner", "--out", str(out), "--no-views"]) == 0
    assert sorted(p.name for p in (out / "my_design").iterdir()) == ["corner"]


@pytest.mark.parametrize("suffix", [":nope", "_missing.py"])
def test_rejects_unknown_designs(design: Path, suffix: str) -> None:
    target = f"{design}{suffix}" if suffix.startswith(":") else str(design).replace(".py", suffix)
    with pytest.raises(SystemExit):
        main(["export", target])


def test_rejects_a_file_without_assemblies(tmp_path: Path) -> None:
    path = tmp_path / "empty.py"
    path.write_text("x = 1\n")
    with pytest.raises(SystemExit):
        main(["export", str(path)])
