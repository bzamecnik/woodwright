"""Cuts on a single board."""

from woodwright.assembly import Assembly
from woodwright.cuts import Mortise
from woodwright.part import Board
from woodwright.stock import Stock

THICK_OAK = Stock.board(thickness=40, species="oak")


def _board(name: str, stock: Stock) -> tuple[Assembly, Board]:
    asm = Assembly(name)
    board = asm.add(Board("board", stock, length=600, width=300))
    return asm, board


def dado(
    start: float = 100, width: float = 30, depth: float = 10, stock: Stock = THICK_OAK
) -> Assembly:
    """A dado: a groove across the grain, from edge to edge."""
    asm, board = _board("dado", stock)
    board.cut(
        Mortise(board.top_face, start=start, length=width, offset=0, width=board.width, depth=depth)
    )
    return asm


def groove(
    offset: float = 50, width: float = 10, depth: float = 20, stock: Stock = THICK_OAK
) -> Assembly:
    """A groove along the grain, from end to end."""
    asm, board = _board("groove", stock)
    board.cut(
        Mortise(
            board.top_face, start=0, length=board.length, offset=offset, width=width, depth=depth
        )
    )
    return asm


def rabbet(width: float = 10, depth: float = 20, stock: Stock = THICK_OAK) -> Assembly:
    """A rabbet along an edge: a groove open to the edge."""
    asm, board = _board("rabbet", stock)
    board.cut(
        Mortise(board.top_face, start=0, length=board.length, offset=0, width=width, depth=depth)
    )
    return asm


def end_rabbet(width: float = 30, depth: float = 10, stock: Stock = THICK_OAK) -> Assembly:
    """A rabbet at an end: a dado open to the end grain."""
    asm, board = _board("end_rabbet", stock)
    board.cut(
        Mortise(board.top_face, start=0, length=width, offset=0, width=board.width, depth=depth)
    )
    return asm
