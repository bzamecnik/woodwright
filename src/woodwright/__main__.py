"""`python -m woodwright`: the same as the `woodwright` command."""

import sys

from woodwright.cli import main

if __name__ == "__main__":
    sys.exit(main(prog="python -m woodwright"))
