"""Cuts on a single board."""

from woodwright.assembly import Assembly
from woodwright.cuts import (
    Chamfer,
    Dado,
    EndRabbet,
    Groove,
    Mitre,
    Mortise,
    Rabbet,
    SlotMortise,
    Taper,
    Tenon,
    Tongue,
)
from woodwright.examples._common import THIN_OAK
from woodwright.part import Board
from woodwright.stock import Stock

THICK_OAK = Stock.board(thickness=40, species="oak")


def _board(
    name: str, stock: Stock, length: float = 600, width: float = 300
) -> tuple[Assembly, Board]:
    asm = Assembly(name)
    board = asm.add(Board("board", stock, length=length, width=width))
    return asm, board


def dado(
    distance: float = 100, width: float = 30, depth: float = 10, stock: Stock = THICK_OAK
) -> Assembly:
    """A dado: a groove across the grain, from edge to edge."""
    asm, board = _board("dado", stock)
    board.cut(Dado(board.top_face, width=width, depth=depth, distance=distance))
    return asm


def groove(
    distance: float = 50, width: float = 10, depth: float = 20, stock: Stock = THICK_OAK
) -> Assembly:
    """A groove along the grain, from end to end."""
    asm, board = _board("groove", stock)
    board.cut(Groove(board.top_face, width=width, depth=depth, distance=distance))
    return asm


def stopped_groove(
    distance: float = 50,
    width: float = 10,
    depth: float = 20,
    stop: float = 40,
    stock: Stock = THICK_OAK,
) -> Assembly:
    """A groove stopped `stop` short of both ends, so it shows at neither."""
    asm, board = _board("stopped_groove", stock)
    board.cut(
        Groove(
            board.top_face,
            width=width,
            depth=depth,
            distance=distance,
            stopped={board.left_end: stop, board.right_end: stop},
        )
    )
    return asm


def rabbet(width: float = 10, depth: float = 20, stock: Stock = THICK_OAK) -> Assembly:
    """A rabbet along an edge: a groove open to the edge."""
    asm, board = _board("rabbet", stock)
    board.cut(Rabbet(board.top_face, at=board.front_edge, width=width, depth=depth))
    return asm


def stopped_rabbet(
    width: float = 10, depth: float = 20, stop: float = 40, stock: Stock = THICK_OAK
) -> Assembly:
    """A rabbet along the back edge stopped short of the right end, e.g. in the
    side of a case for a back that stops below the top."""
    asm, board = _board("stopped_rabbet", stock)
    board.cut(
        Rabbet(
            board.top_face,
            at=board.back_edge,
            width=width,
            depth=depth,
            stopped={board.right_end: stop},
        )
    )
    return asm


def end_rabbet(width: float = 30, depth: float = 10, stock: Stock = THICK_OAK) -> Assembly:
    """A rabbet at an end: a dado open to the end grain."""
    asm, board = _board("end_rabbet", stock)
    board.cut(EndRabbet(board.top_face, at=board.left_end, width=width, depth=depth))
    return asm


def slot_mortise(width: float = 14, depth: float = 60, stock: Stock = THICK_OAK) -> Assembly:
    """A slot in an end, through the width, centered in the thickness (for a bridle)."""
    asm, board = _board("slot_mortise", stock, width=60)
    board.cut(SlotMortise(board.left_end, width=width, depth=depth))
    return asm


def mortise(depth: float = 30, stock: Stock = THICK_OAK) -> Assembly:
    """A blind mortise in an edge (a through one when as deep as the board is wide)."""
    asm, board = _board("mortise", stock, width=60)
    board.cut(Mortise(board.back_edge, start=275, length=50, offset=13, width=14, depth=depth))
    return asm


def tenon(
    length: float = 40, thickness: float = 14, width: float = 50, stock: Stock = THICK_OAK
) -> Assembly:
    """A tenon on an end, with shoulders and cheeks; the board grows by its length."""
    asm, board = _board("tenon", stock, width=60)
    board.cut(Tenon(board.right_end, length=length, thickness=thickness, width=width))
    return asm


def tongue(length: float = 10, thickness: float = 12, stock: Stock = THICK_OAK) -> Assembly:
    """A tongue along an edge; the board grows by its length."""
    asm, board = _board("tongue", stock, width=150)
    board.cut(Tongue(board.back_edge, length=length, thickness=thickness))
    return asm


def chamfer(size: float = 5, stock: Stock = THICK_OAK) -> Assembly:
    """Chamfers on the four arrises along the grain."""
    asm, board = _board("chamfer", stock, width=60)
    for face in (board.top_face, board.bottom_face):
        for edge in (board.front_edge, board.back_edge):
            board.cut(Chamfer(board.arris(face, edge), size=size))
    return asm


def mitre(angle: float = 45, stock: Stock = THICK_OAK) -> Assembly:
    """Both ends mitred across the face, as a picture frame member; back edge inside."""
    asm, board = _board("mitre", stock, width=60)
    for end in (board.left_end, board.right_end):
        board.cut(Mitre(end, inside=board.back_edge, angle=angle))
    return asm


def edge_mitre(angle: float = 45, stock: Stock = THICK_OAK) -> Assembly:
    """An end mitred across the edge, as for a carcase corner; bottom face inside."""
    asm, board = _board("edge_mitre", stock)
    board.cut(Mitre(board.right_end, inside=board.bottom_face, angle=angle))
    return asm


def rabbeted_panel(
    length: float = 400, width: float = 250, rabbet: float = 15, depth: float = 5
) -> Assembly:
    """A thin panel rabbeted on all four sides, to fit a groove in a frame or a drawer."""
    asm, board = _board("rabbeted_panel", THIN_OAK, length=length, width=width)
    for at in (board.front_edge, board.back_edge, board.left_end, board.right_end):
        board.cut(Rabbet(board.top_face, at=at, width=rabbet, depth=depth))
    return asm


def tapered_panel(
    length: float = 400,
    width: float = 300,
    taper_width: float = 30,
    edge_thickness: float = 6,
) -> Assembly:
    """A drawer bottom with three edges tapered on the underside to fit grooves.

    The underside is planed at a slope `taper_width` wide, leaving the edge
    as thick as the groove is wide. The back edge stays square: it goes
    under the back of the drawer.
    """
    asm, board = _board("tapered_panel", THIN_OAK, length=length, width=width)
    amount = board.thickness - edge_thickness
    for at in (board.front_edge, board.left_end, board.right_end):
        board.cut(Chamfer(board.arris(board.bottom_face, at), size=taper_width, size_b=amount))
    return asm


def wedge(
    length: float = 100, width: float = 20, tip: float = 2, stock: Stock = THIN_OAK
) -> Assembly:
    """A wedge, e.g. for a wedged tenon: both edges tapered towards the right end."""
    asm, board = _board("wedge", stock, length=length, width=width)
    for edge in (board.front_edge, board.back_edge):
        board.cut(Taper(edge, end=board.right_end, amount=(width - tip) / 2))
    return asm


def tapered_leg(
    length: float = 450, width: float = 40, taper: float = 15, taper_length: float = 300
) -> Assembly:
    """A leg tapered on its two inside sides over the lower part of its length."""
    asm, board = _board("tapered_leg", Stock.board(thickness=40, species="oak"), length, width)
    for side in (board.back_edge, board.bottom_face):
        board.cut(Taper(side, end=board.left_end, amount=taper, length=taper_length))
    return asm
