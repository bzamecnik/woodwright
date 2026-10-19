"""Render the pictures for the README: `uv run python docs/images/render.py`."""

import re
from pathlib import Path

from woodwright.examples import projects
from woodwright.export import exploded, svg_view

HERE = Path(__file__).parent
LINE_WEIGHT = 1.5  # mm, for a chair about 1 m tall shown some 450 px tall


def render(shape, path: Path) -> None:
    svg_view(shape, path, hidden_lines=False, line_weight=LINE_WEIGHT)
    # A white background, so that the lines show in a dark theme too.
    text = path.read_text()
    x, y, w, h = re.search(r'viewBox="([^"]*)"', text)[1].split()
    background = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="white" />'
    path.write_text(re.sub(r"(<svg[^>]*>)", rf"\1\n  {background}", text, count=1))


model = projects.chair().resolve()
render(model.compound(), HERE / "chair.svg")
render(exploded(model), HERE / "chair_exploded.svg")
