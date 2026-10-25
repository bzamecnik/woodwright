"""The example gallery of the docs, from the examples' code and their exports.

    uv run docs/gallery.py                      # exports from output/
    uv run docs/gallery.py --exports build/examples

Writes `docs/gallery/`: an index of all examples by group, a page per
example (its description, pictures, parameters, drawings, cut list, plans
and code) and a page of tags, by the joints and cuts each example uses.

Nothing is rendered here, so it takes seconds: the pictures, drawings and
plans are copied from the exports `woodwright export` made (`--all` for
every example, a few minutes). An example not exported gets its page
without them; one exported before its code changed is marked as stale.
"""

import argparse
import filecmp
import inspect
import json
import re
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

from woodwright.assembly import Assembly
from woodwright.examples import ALL, cuts, frames, joints, name, projects
from woodwright.export import source_hash
from woodwright.stock import Stock

DOCS = Path(__file__).parent
GALLERY = DOCS / "gallery"
SOURCE_URL = "https://github.com/bzamecnik/woodwright/blob/master/src/woodwright/examples"
GROUPS: list[tuple[str, ModuleType]] = [
    ("Cuts", cuts),
    ("Joints", joints),
    ("Frames", frames),
    ("Projects", projects),
]
# Joints whose class names don't read well as tags.
JOINT_TAGS = {"DadoJoint": "dado", "RabbetJoint": "rabbet", "GrooveJoint": "groove"}

Example = Callable[[], Assembly]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--exports", type=Path, default=Path("output"), help="default: %(default)s")
    args = parser.parse_args()

    written: set[Path] = set()
    examples = {name(example): Entry(example, args.exports) for example in ALL}
    for entry in examples.values():
        written |= entry.write()
    written.add(write(GALLERY / "index.md", index(list(examples.values()), args.exports)))
    written.add(write(GALLERY / "tags.md", TAGS_PAGE))
    removed = prune(written)

    rendered = sum(
        entry.meta is not None or entry.has("assembled.svg") for entry in examples.values()
    )
    stale = [key for key, entry in examples.items() if entry.stale]
    print(f"{len(examples)} examples, {rendered} with exports from {args.exports} -> {GALLERY}")
    if stale:
        names = " ".join(stale) if len(stale) <= 10 else "--all"
        print(f"{len(stale)} exported from older code, refresh them:", file=sys.stderr)
        print(f"  uv run woodwright export {names}", file=sys.stderr)
    if removed:
        print(f"removed {removed} files no longer generated")
    return 0


class Entry:
    """An example, its code and its exports."""

    def __init__(self, example: Example, exports: Path) -> None:
        self.example = example
        self.name = name(example)
        self.group, self.function = self.name.split(".")
        self.exports = exports / self.group / self.function
        self.code = inspect.getsource(example)
        meta = self.exports / "meta.json"
        self.meta = json.loads(meta.read_text()) if meta.is_file() else None
        self.page_dir = GALLERY / self.group / self.function

    def has(self, file: str) -> bool:
        return (self.exports / file).is_file()

    @property
    def stale(self) -> bool:
        """Exported from other code than the example's now (or exported
        before exports recorded their code)."""
        if not self.has("cut_list.txt"):
            return False
        return self.meta is None or self.meta.get("source_hash") != source_hash(self.code)

    @property
    def title(self) -> str:
        return self.function.replace("_", " ").capitalize()

    @property
    def summary(self) -> str:
        doc = inspect.getdoc(self.example) or ""
        return doc.split("\n\n")[0].replace("\n", " ")

    def drawings(self) -> list[Path]:
        """The drawing sheets, in the order of the plans: the assembly, its
        parts, then each part."""
        first = {"assembly": 0, "parts": 1}
        sheets = (self.exports / "drawings").glob("*.svg")
        return sorted(sheets, key=lambda sheet: (first.get(sheet.stem, 2), sheet.stem))

    def tags(self) -> list[str]:
        """The kinds of joints between its parts and of cuts added to them."""
        assembly = self.example()
        kinds = [_joint_tag(type(joint).__name__) for joint in assembly.joints]
        kinds += [_words(type(cut).__name__) for part in assembly.parts for cut in part.cuts]
        return sorted(set(kinds))

    def write(self) -> set[Path]:
        written = set()
        assets = ["assembled.svg", "exploded.svg", "plans.pdf"]
        assets += [f"drawings/{d.name}" for d in self.drawings()]
        for asset in assets:
            if self.has(asset):
                written.add(copy(self.exports / asset, self.page_dir / asset))
        written.add(write(self.page_dir / "index.md", self.page()))
        return written

    def page(self) -> str:
        doc = inspect.getdoc(self.example) or ""
        tags = self.tags()
        lines = ["---", "tags:", *(f"  - {tag}" for tag in tags), "---", ""] if tags else []
        lines += [f"# {self.title}", "", f"`{self.name}`", "", doc, ""]
        command = f"woodwright export {self.name}"
        if not self.has("cut_list.txt"):
            lines += [
                '!!! note "Not exported yet"',
                "",
                f"    Its pictures, drawings and plans appear here once exported: `{command}`",
                "",
            ]
        elif self.stale:
            changed = (
                "The example's code has changed since these files were exported"
                if self.meta
                else "These files were exported without a record of the code they came from"
            )
            lines += [
                '!!! warning "Exported from older code"',
                "",
                f"    {changed}; they may not match it. Refresh them: `{command}`",
                "",
            ]
        pictures = [f for f in ("assembled.svg", "exploded.svg") if self.has(f)]
        if pictures:
            lines += ['<div class="grid" markdown>', ""]
            for picture in pictures:  # each in a paragraph of its own: a cell of the grid
                lines += [f"![{self.title}, {picture[:-4]}]({picture}){{ loading=lazy }}", ""]
            lines += ["</div>", ""]

        lines += ["## Parameters", "", *parameters(self.example), ""]
        lines += [
            "Change them in a design file"
            " (see [Change an example](../../../tutorials/parameters.md)):",
            "",
            "```py",
            f"from woodwright.examples import {self.group}",
            "",
            f"design = {self.name}({_first_parameter(self.example)})",
            "```",
            "",
        ]

        drawings = self.drawings()
        if drawings or self.has("plans.pdf"):
            lines += ["## Drawings", ""]
            if self.has("plans.pdf"):
                lines += ["The plans in one PDF: [plans.pdf](plans.pdf).", ""]
            for drawing in drawings:
                label = drawing.stem.replace("_", " ")
                path = f"drawings/{drawing.name}"
                lines += [
                    f'??? note "{label.capitalize()}"',
                    "",
                    f"    [![{label}]({path}){{ loading=lazy }}]({path})",
                    "",
                ]
        if self.has("cut_list.txt"):
            cut_list = (self.exports / "cut_list.txt").read_text().rstrip()
            lines += ["## Cut list", "", "```text", cut_list, "```", ""]

        module = Path(inspect.getsourcefile(self.example) or "").name
        line = inspect.getsourcelines(self.example)[1]
        lines += [
            "## Code",
            "",
            f"From [`woodwright/examples/{module}`]({SOURCE_URL}/{module}#L{line}),"
            " which imports the names it uses (see"
            " [From an example to your own design](../../../tutorials/own-design.md)):",
            "",
            "```python",
            self.code.rstrip(),
            "```",
            "",
        ]
        if self.meta:
            lines += [
                f"*Exported with woodwright {self.meta['woodwright']} on {self.meta['date']}.*",
                "",
            ]
        return "\n".join(lines)


def parameters(example: Example) -> list[str]:
    """The example's parameters and their defaults, as a Markdown table."""
    rows = ["| Parameter | Default |", "| --- | --- |"]
    for parameter in inspect.signature(example).parameters.values():
        rows.append(f"| `{parameter.name}` | {_default(parameter.default)} |")
    return rows if len(rows) > 2 else ["None: it is one fixed design."]


def _default(value: object) -> str:
    if isinstance(value, Stock):
        kind = f"ø{value.diameter:g} mm rod" if value.round else f"{value.thickness:g} mm board"
        return f"{kind}, {value.species}" if value.species else kind
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"`{value!r}`"


def _first_parameter(example: Example) -> str:
    for parameter in inspect.signature(example).parameters.values():
        if isinstance(parameter.default, int | float) and not isinstance(parameter.default, bool):
            default = parameter.default
            return f"{parameter.name}={default * 1.25:g}"
    return ""


def _words(class_name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", " ", class_name).lower()


def _joint_tag(class_name: str) -> str:
    return JOINT_TAGS.get(class_name) or _words(class_name).replace(
        "mortise tenon", "mortise and tenon"
    )


def index(entries: list[Entry], exports: Path) -> str:
    exported = sum(entry.has("cut_list.txt") for entry in entries)
    lines = [
        "# Examples",
        "",
        f"{len(entries)} examples, from single cuts and joints to whole projects."
        " Each is a function in `woodwright.examples` with its sizes as parameters;"
        " its page has its pictures, drawings, cut list and code."
        " Find them by joint or cut in the [tags](tags.md).",
        "",
    ]
    if exported < len(entries):
        lines += [
            '!!! note "Pictures"',
            "",
            f"    {exported} of {len(entries)} examples are exported in `{exports}`."
            " For the pictures of all of them, export them and build the gallery again:",
            "",
            "    ```shell",
            "    uv run woodwright export --all",
            "    uv run docs/gallery.py",
            "    ```",
            "",
        ]
    for title, module in GROUPS:
        members = [entry for entry in entries if entry.group == module.__name__.rsplit(".")[-1]]
        doc = (inspect.getdoc(module) or "").split("\n\n")[0].replace("\n", " ")
        lines += [f"## {title}", "", doc, "", '<div class="grid cards" markdown>', ""]
        for entry in members:
            link = f"{entry.group}/{entry.function}/index.md"
            lines.append(f"-   **[{entry.title}]({link})**")
            lines.append("")
            if entry.has("assembled.svg"):
                picture = f"{entry.group}/{entry.function}/assembled.svg"
                lines += [f"    [![{entry.title}]({picture}){{ loading=lazy }}]({link})", ""]
            lines += [f"    {entry.summary}", ""]
        lines += ["</div>", ""]
    return "\n".join(lines)


TAGS_PAGE = """# Examples by tag

Each example is tagged by the joints between its parts and the cuts added
to them.

<!-- material/tags -->
"""


def write(path: Path, text: str) -> Path:
    """Write a file unless it already has this text (so that a running
    `zensical serve` rebuilds only what changed)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file() or path.read_text() != text:
        path.write_text(text)
    return path


def copy(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.is_file() or not filecmp.cmp(source, target, shallow=False):
        shutil.copyfile(source, target)
    return target


def prune(written: set[Path]) -> int:
    """Remove files in the gallery left from earlier runs, then empty folders."""
    removed = 0
    for path in sorted(GALLERY.rglob("*"), reverse=True):
        if path.is_file() and path not in written:
            path.unlink()
            removed += 1
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    return removed


if __name__ == "__main__":
    raise SystemExit(main())
