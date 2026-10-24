"""Render the pictures for the README: `uv run python docs/images/render.py`."""

import re
import shutil
import tempfile
from pathlib import Path

from woodwright.cli import main
from woodwright.examples import projects
from woodwright.export import exploded, svg_view

HERE = Path(__file__).parent
LINE_WEIGHT = 1.5  # mm, for a chair about 1 m tall shown some 450 px tall


def render(shape, path: Path, line_weight: float = LINE_WEIGHT) -> None:
    svg_view(shape, path, hidden_lines=False, line_weight=line_weight)
    # A white background, so that the lines show in a dark theme too.
    text = path.read_text()
    x, y, w, h = re.search(r'viewBox="([^"]*)"', text)[1].split()
    background = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="white" />'
    path.write_text(re.sub(r"(<svg[^>]*>)", rf"\1\n  {background}", text, count=1))


model = projects.chair().resolve()
render(model.compound(), HERE / "chair.svg")
render(exploded(model), HERE / "chair_exploded.svg")

# About twice as wide as the chair is tall, shown at about the same width.
model = projects.workbench().resolve()
render(model.compound(), HERE / "workbench.svg", line_weight=2 * LINE_WEIGHT)
render(exploded(model), HERE / "workbench_exploded.svg", line_weight=2 * LINE_WEIGHT)

# The table's plans, exported as by the command line, and two of its sheets:
# the parts (page 5) and an apron (page 7).
with tempfile.TemporaryDirectory() as tmp:
    main(["export", "projects.table", "--out", tmp])
    table = Path(tmp) / "projects" / "table"
    shutil.copy(table / "plans.pdf", HERE / "table_plans.pdf")
    shutil.copy(table / "drawings" / "parts.svg", HERE / "table_parts.svg")
    shutil.copy(table / "drawings" / "apron_front_back.svg", HERE / "table_apron.svg")
