"""Frames of stiles and rails."""

from woodwright.assembly import Assembly
from woodwright.examples._common import OAK, STANDING
from woodwright.joints import MortiseTenon
from woodwright.part import Board
from woodwright.placement import Offset
from woodwright.stock import Stock


def mortise_tenon_frame(
    stile_length: float = 600,
    rail_length: float = 300,
    width: float = 60,
    shoulder: float = 10,
    stock: Stock = OAK,
) -> Assembly:
    """Two stiles and two rails, the rails tenoned into the stiles at their ends."""
    asm = Assembly("mortise_tenon_frame", root_location=STANDING)
    stile_left = asm.add(Board("stile_left", stock, length=stile_length, width=width))
    stile_right = asm.add(Board("stile_right", stock, length=stile_length, width=width))
    rail_top = asm.add(Board("rail_top", stock, length=rail_length, width=width))
    rail_bottom = asm.add(Board("rail_bottom", stock, length=rail_length, width=width))
    # The stiles face each other with opposite edges, so the same rail end
    # sits at opposite ends of their edges.
    at_start = Offset(0)
    at_end = Offset(stile_length - width)
    for tenon, mortise, position in [
        (rail_top.left_end, stile_left.back_edge, at_start),
        (rail_top.right_end, stile_right.front_edge, at_end),
        (rail_bottom.left_end, stile_left.back_edge, at_end),
        (rail_bottom.right_end, stile_right.front_edge, at_start),
    ]:
        asm.join(MortiseTenon(tenon=tenon, mortise=mortise, position=position, shoulder=shoulder))
    return asm
