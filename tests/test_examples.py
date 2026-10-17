import pytest

from woodwright.examples import ALL


@pytest.mark.parametrize("example", ALL, ids=lambda example: example.__name__)
def test_example_resolves(example) -> None:
    example().resolve().compound()
