"""List and export the examples: `python -m woodwright.examples {list,export}`.

The same as the `woodwright` command (see `woodwright.cli`).
"""

import sys

from woodwright.cli import main as _main


def main(argv: list[str] | None = None) -> int:
    return _main(argv, prog="python -m woodwright.examples")


if __name__ == "__main__":
    sys.exit(main())
