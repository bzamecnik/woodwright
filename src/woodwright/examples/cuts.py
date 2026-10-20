"""Cuts on a single part: a board, or a rod of round stock."""

from woodwright.assembly import Assembly
from woodwright.cuts import (
    Chamfer,
    Dado,
    EndChamfer,
    EndRabbet,
    Flat,
    Groove,
    Hole,
    Mitre,
    Mortise,
    Rabbet,
    RoundTaper,
    SlotMortise,
    Taper,
    Tenon,
    Tongue,
)
from woodwright.examples._common import OAK, THIN_OAK
from woodwright.part import Board, Rod
from woodwright.stock import Stock

THICK_OAK = Stock.board(thickness=40, species="oak")
DOWEL_OAK = Stock.rod(diameter=10, species="oak")
THICK_DOWEL_OAK = Stock.rod(diameter=16, species="oak")
ROD_OAK = Stock.rod(diameter=25, species="oak")
LEG_OAK = Stock.rod(diameter=40, species="oak")


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


# --- Holes ------------------------------------------------------------------


def through_hole(diameter: float = 20, stock: Stock = THICK_OAK) -> Assembly:
    """A hole through a board, 80 from its left end, centered across it."""
    asm, board = _board("through_hole", stock, length=300, width=100)
    board.cut(Hole(board.top_face, diameter, at={board.left_end: 80}))
    return asm


def blind_hole(
    diameter: float = 12, depth: float = 25, point: float | None = None, stock: Stock = THICK_OAK
) -> Assembly:
    """Blind holes, flat-bottomed (Forstner, auger) or with `point`, the
    angle of a twist drill's tip, a conical point below `depth`."""
    asm, board = _board("blind_hole", stock, length=300, width=100)
    for distance in (60, 150, 240):
        at = {board.left_end: distance, board.front_edge: 35}
        board.cut(Hole(board.top_face, diameter, depth=depth, at=at, point=point))
    return asm


def counterbored_hole(stock: Stock = OAK) -> Assembly:
    """A clearance hole for a 5 mm screw, counterbored for its head and a
    10 mm plug over it, e.g. in a batten screwed to a door."""
    asm, board = _board("counterbored_hole", stock, length=300, width=60)
    for end in (board.left_end, board.right_end):
        board.cut(Hole(board.top_face, 5.5, at={end: 40}, counterbore=10, counterbore_depth=8))
    return asm


def countersunk_hole(stock: Stock = OAK) -> Assembly:
    """Clearance holes for 5 mm screws, countersunk for their heads (90 degrees)."""
    asm, board = _board("countersunk_hole", stock, length=300, width=60)
    for end in (board.left_end, board.right_end):
        board.cut(Hole(board.top_face, 5.5, at={end: 40}, countersink=11))
    return asm


def tapered_hole(stock: Stock = THICK_OAK) -> Assembly:
    """Reamed, tapered holes through a Windsor seat for the legs, wider below.

    The legs aren't splayed yet (angled holes come later)."""
    asm, board = _board("tapered_hole", stock, length=420, width=380)
    for end in (board.left_end, board.right_end):
        for edge in (board.front_edge, board.back_edge):
            board.cut(Hole(board.bottom_face, 28, bottom_diameter=20, at={end: 70, edge: 70}))
    return asm


def shelf_pin_holes(
    height: float = 700,
    depth: float = 300,
    pitch: float = 32,
    count: int = 12,
    stock: Stock = OAK,
) -> Assembly:
    """Two rows of 5 mm holes, 12 deep, in the inside of a case side for
    shelf pins, `pitch` apart (the 32 mm system), 37 from the edges."""
    asm, board = _board("shelf_pin_holes", stock, length=height, width=depth)
    start = (height - (count - 1) * pitch) / 2
    for i in range(count):
        for edge in (board.front_edge, board.back_edge):
            at = {board.left_end: start + i * pitch, edge: 37}
            board.cut(Hole(board.top_face, 5, depth=12, at=at, point=118))
    return asm


def dowel_holes(diameter: float = 8, stock: Stock = OAK) -> Assembly:
    """Holes for dowels: in an edge, for an edge joint (half the dowel's
    length, 15, deep), and in an end, for a frame corner (25 deep)."""
    asm, board = _board("dowel_holes", stock, length=400, width=80)
    for distance in (50, 200, 350):
        board.cut(Hole(board.front_edge, diameter, depth=15, at={board.left_end: distance}))
    for distance in (20, 60):
        board.cut(Hole(board.right_end, diameter, depth=25, at={board.front_edge: distance}))
    return asm


def chamfered_foot(size: float = 3, stock: Stock = THICK_OAK) -> Assembly:
    """A square leg chamfered around its foot, so that it doesn't splinter."""
    asm, board = _board("chamfered_foot", stock, length=450, width=40)
    board.cut(EndChamfer(board.left_end, size))
    return asm


# --- Rods -------------------------------------------------------------------


def _rod(name: str, stock: Stock, length: float) -> tuple[Assembly, Rod]:
    asm = Assembly(name)
    rod = asm.add(Rod("rod", stock, length=length))
    return asm, rod


def rod(length: float = 380, stock: Stock = ROD_OAK) -> Assembly:
    """A plain rod, e.g. a ladder rung, a rail: round stock cut to length."""
    asm, _ = _rod("rod", stock, length)
    return asm


def dowel(length: float = 40, chamfer: float = 1, stock: Stock = DOWEL_OAK) -> Assembly:
    """A dowel chamfered at both ends, so that it enters its holes."""
    asm, dowel = _rod("dowel", stock, length)
    for end in (dowel.left_end, dowel.right_end):
        dowel.cut(EndChamfer(end, chamfer))
    return asm


def peg(length: float = 60, point: float = 15, stock: Stock = DOWEL_OAK) -> Assembly:
    """A peg (a pin) pointed at its right end, e.g. for a drawbored tenon;
    its other end is chamfered."""
    asm, peg = _rod("peg", stock, length)
    peg.cut(RoundTaper(peg.right_end, 0, length=point))
    peg.cut(EndChamfer(peg.left_end, 1))
    return asm


def round_tapered_leg(
    length: float = 450,
    foot: float = 28,
    taper_length: float = 300,
    stock: Stock = LEG_OAK,
) -> Assembly:
    """A round leg tapering (a cone, as turned) towards its foot over its
    lower part, chamfered around the foot."""
    asm, leg = _rod("round_tapered_leg", stock, length)
    leg.cut(RoundTaper(leg.left_end, foot, length=taper_length))
    leg.cut(EndChamfer(leg.left_end, 2))
    return asm


def tapered_rod(length: float = 300, stock: Stock = ROD_OAK) -> Assembly:
    """A rod tapering to a cone over its whole length, e.g. a spindle."""
    asm, rod = _rod("tapered_rod", stock, length)
    rod.cut(RoundTaper(rod.right_end, 15))
    return asm


def flat_tapered_dowel(
    length: float = 120, amount: float = 8, stock: Stock = THICK_DOWEL_OAK
) -> Assembly:
    """A dowel tapered flat (a sloping plane, not a cone) on one side
    towards its right end, e.g. a wedge driven through the tenon of a
    dowel tusk joint."""
    asm, rod = _rod("flat_tapered_dowel", stock, length)
    rod.cut(Taper(rod.top_face, end=rod.right_end, amount=amount, length=length - 20))
    return asm


def half_dowel(length: float = 120, stock: Stock = THICK_DOWEL_OAK) -> Assembly:
    """A dowel ripped in half along its length, its flat side down: e.g. the
    bearing of a dowel tusk wedge, glued flat on a board."""
    asm, rod = _rod("half_dowel", stock, length)
    rod.cut(Flat(rod.bottom_face, stock.diameter / 2))
    return asm


def rod_with_flats(length: float = 380, stock: Stock = ROD_OAK) -> Assembly:
    """A rod with flats planed at both ends on its underside, e.g. where it
    lies on a pair of brackets, so that it doesn't roll."""
    asm, rod = _rod("rod_with_flats", stock, length)
    rod.cut(Flat(rod.bottom_face, 3, stopped={rod.right_end: length - 50}))
    rod.cut(Flat(rod.bottom_face, 3, stopped={rod.left_end: length - 50}))
    return asm


def mitred_rod(angle: float = 45, stock: Stock = ROD_OAK) -> Assembly:
    """A rod mitred at both ends, e.g. a towel rail's corner."""
    asm, rod = _rod("mitred_rod", stock, 300)
    for end in (rod.left_end, rod.right_end):
        rod.cut(Mitre(end, inside=rod.back_edge, angle=angle))
    return asm


def drilled_rod(length: float = 200, stock: Stock = ROD_OAK) -> Assembly:
    """A rod with a cross hole through it near one end (e.g. for a peg) and
    a blind hole into its other end, on its axis (e.g. for a dowel)."""
    asm, rod = _rod("drilled_rod", stock, length)
    rod.cut(Hole(rod.top_face, 8, at={rod.left_end: 25}))
    rod.cut(Hole(rod.right_end, 10, depth=30, point=118))
    return asm
