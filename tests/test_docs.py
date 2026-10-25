"""The code in the documentation runs and prints what the docs say.

On each page, the ```python blocks run in order in one namespace (in a
temporary folder); a block's printed output must equal the ```text block
right after it. Fragments that don't run on their own are marked ```py.
The design notes (vision, plan, ...) sketch APIs to come and aren't run.
"""

import contextlib
import io
import re
from pathlib import Path

import pytest

DOCS = Path(__file__).parent.parent / "docs"
DESIGN_NOTES = {"vision.md", "plan.md", "validation.md", "initial_vision.md"}
BLOCK = re.compile(r"^( *)```(\w*)[^\n]*\n(.*?)^\1```", re.MULTILINE | re.DOTALL)


def _pages() -> list[Path]:
    return sorted(
        page
        for page in DOCS.rglob("*.md")
        if "```python" in page.read_text()
        and page.name not in DESIGN_NOTES
        and "gallery" not in page.parts
    )


def _blocks(page: Path) -> list[tuple[str, str]]:
    """(language, code) of each fenced block, dedented."""
    blocks = []
    for match in BLOCK.finditer(page.read_text()):
        indent, language, body = match.groups()
        lines = [line.removeprefix(indent) for line in body.splitlines()]
        blocks.append((language, "\n".join(lines) + "\n"))
    return blocks


@pytest.mark.parametrize("page", _pages(), ids=lambda page: str(page.relative_to(DOCS)))
def test_code_runs(page: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    namespace: dict[str, object] = {"__name__": "__docs__"}
    blocks = _blocks(page)
    for i, (language, code) in enumerate(blocks):
        if language != "python":
            continue
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(compile(code, f"{page.name}, block {i + 1}", "exec"), namespace)
        printed = output.getvalue()
        if printed and i + 1 < len(blocks) and blocks[i + 1][0] == "text":
            assert printed.strip() == blocks[i + 1][1].strip(), f"block {i + 1}"
