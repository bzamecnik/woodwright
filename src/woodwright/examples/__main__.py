"""List and export the examples: `python -m woodwright.examples {list,export}`."""

import argparse
import sys
from pathlib import Path

from woodwright.examples import ALL, get, name
from woodwright.export import export_model


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m woodwright.examples", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list the examples")
    export = commands.add_parser("export", help="export examples to STEP, STL, SVG and cut lists")
    export.add_argument("names", nargs="*", help="examples to export, e.g. frames.bridle_frame")
    export.add_argument("--all", action="store_true", help="export all examples")
    export.add_argument("--out", type=Path, default=Path("output"), help="default: %(default)s")
    export.add_argument("--no-views", action="store_true", help="skip the (slow) SVG views")
    args = parser.parse_args(argv)

    if args.command == "list":
        for example in ALL:
            doc = (example.__doc__ or "").strip().splitlines()
            print(f"{name(example):40} {doc[0] if doc else ''}")
        return 0

    if args.all == bool(args.names):
        parser.error("give either example names or --all")
    try:
        examples = ALL if args.all else [get(n) for n in args.names]
    except KeyError as e:
        parser.error(e.args[0])
    for example in examples:
        out_dir = args.out.joinpath(*name(example).split("."))
        export_model(example().resolve(), out_dir, views=not args.no_views)
        print(f"{name(example)} -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
