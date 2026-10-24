"""The `woodwright` command: list the examples, export them or your own designs.

    woodwright list
    woodwright export projects.cabinet_door
    woodwright export my_door.py

A design file is a Python file defining assemblies: each `Assembly` assigned
to a variable, and each function returning one that needs no arguments
(e.g. a copied example), is exported to `<out>/<file name>/<name>`; with
`my_door.py:door` only the one named. For example:

    from woodwright.examples import projects

    door = projects.cabinet_door(height=700, width=450)
"""

import argparse
import inspect
import runpy
import sys
from collections.abc import Callable, Iterator
from importlib.metadata import version
from pathlib import Path

from woodwright.assembly import Assembly
from woodwright.examples import ALL, get, name
from woodwright.export import export_model
from woodwright.pdf import Source

_RUN_NAME = "__woodwright__"  # so that `if __name__ == "__main__":` blocks don't run


def _returns_assembly(function: Callable[..., object]) -> bool:
    try:
        signature = inspect.signature(function)
    except ValueError:
        return False
    if signature.return_annotation not in (Assembly, "Assembly"):
        return False
    return all(
        p.default is not p.empty or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
        for p in signature.parameters.values()
    )


def load_designs(path: Path) -> dict[str, Callable[[], Assembly]]:
    """The assemblies a design file defines, by name, in the order defined.

    Variables holding an `Assembly`, and functions defined in the file that
    are annotated to return one and need no arguments; names starting with
    an underscore are left out.
    """
    sys.path.insert(0, str(path.parent.resolve()))  # for the file's own imports
    try:
        namespace = runpy.run_path(str(path), run_name=_RUN_NAME)
    finally:
        sys.path.pop(0)
    designs: dict[str, Callable[[], Assembly]] = {}
    for key, value in namespace.items():
        if key.startswith("_"):
            continue
        if isinstance(value, Assembly):
            designs[key] = lambda value=value: value
        elif (
            inspect.isfunction(value) and value.__module__ == _RUN_NAME and _returns_assembly(value)
        ):
            designs[key] = value
    return designs


def _targets(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> Iterator[tuple[str, Callable[[], Assembly], Source]]:
    """(output path relative to --out, assembly factory, its source) for each
    thing to export."""
    if args.all:
        for example in ALL:
            yield name(example).replace(".", "/"), example, _example_source(example)
    for target in args.names:
        file, _, selected = target.partition(".py:")
        if selected or target.endswith(".py"):
            path = Path(file if selected else target).with_suffix(".py")
            if not path.is_file():
                parser.error(f"no such file: {path}")
            designs = load_designs(path)
            if selected:
                if selected not in designs:
                    parser.error(f"{path} defines no assembly named {selected}")
                designs = {selected: designs[selected]}
            if not designs:
                parser.error(
                    f"{path} defines no assembly: assign one to a variable, e.g. "
                    "`door = projects.cabinet_door(width=450)`, or define a function "
                    "returning one, annotated `-> Assembly`"
                )
            code = path.read_text()
            for key, design in designs.items():
                command = _command(f"{path.name}:{key}" if len(designs) > 1 else path.name)
                yield f"{path.stem}/{key}", design, Source(path.name, code, command)
        else:
            try:
                example = get(target)
            except KeyError as e:
                parser.error(e.args[0])
            yield target.replace(".", "/"), example, _example_source(example)


def _example_source(example: Callable[[], Assembly]) -> Source:
    """An example's function (the helpers it calls are in the same version)."""
    module = inspect.getsourcefile(example)
    label = f"woodwright/examples/{Path(module).name}" if module else "woodwright/examples"
    return Source(
        f"{name(example)}, in {label}", inspect.getsource(example), _command(name(example))
    )


def _command(target: str) -> str:
    return f"uvx --python 3.14 woodwright=={version('woodwright')} export {target}"


def main(argv: list[str] | None = None, prog: str = "woodwright") -> int:
    parser = argparse.ArgumentParser(
        prog=prog,
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list the examples")
    export = commands.add_parser(
        "export",
        help="export examples or your own designs to STEP, STL, SVG views, drawings and cut lists",
    )
    export.add_argument(
        "names",
        nargs="*",
        help="examples (e.g. frames.bridle_frame) or design files (my_door.py, my_door.py:door)",
    )
    export.add_argument("--all", action="store_true", help="export all examples")
    export.add_argument("--out", type=Path, default=Path("output"), help="default: %(default)s")
    export.add_argument(
        "--no-views", action="store_true", help="skip the (slow) SVG views and drawings"
    )
    args = parser.parse_args(argv)

    if args.command == "list":
        for example in ALL:
            doc = (example.__doc__ or "").strip().splitlines()
            print(f"{name(example):40} {doc[0] if doc else ''}")
        return 0

    if args.all == bool(args.names):
        parser.error("give either example names, design files or --all")
    for target, design, source in list(_targets(parser, args)):
        out_dir = args.out / target
        export_model(design().resolve(), out_dir, views=not args.no_views, source=source)
        print(f"{target.replace('/', '.')} -> {out_dir}")
    return 0
