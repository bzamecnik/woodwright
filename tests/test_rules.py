import pytest

from woodwright import rules


@pytest.mark.parametrize(
    ("stock", "expected"),
    [(20, 8), (25, 10), (18, 6), (90, 25)],
)
def test_tenon_thickness_snaps_up_to_a_chisel(stock: float, expected: float) -> None:
    assert rules.tenon_thickness(stock) == expected


def test_tenon_thickness_with_custom_chisels() -> None:
    assert rules.tenon_thickness(20, chisels=(6, 12)) == 12


def test_tenon_length() -> None:
    assert rules.tenon_length(60) == pytest.approx(40)


def test_round_tenon_diameter_snaps_down_to_a_drill() -> None:
    assert rules.round_tenon_diameter(45) == 25
    assert rules.round_tenon_diameter(40) == 22
    assert rules.round_tenon_diameter(5) == 6  # the smallest bit


def test_screw_holes() -> None:
    assert rules.screw_clearance(4) == 4.5
    assert rules.screw_pilot(4) == 3
    assert rules.screw_head(4) == 8
