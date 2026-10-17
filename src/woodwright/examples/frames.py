"""Frames of two stiles and two rails, and a frame with a panel."""

from collections.abc import Callable

from woodwright.assembly import Assembly
from woodwright.examples._common import OAK, STANDING, THIN_OAK
from woodwright.joints import Bridle, GrooveJoint, HalfLap, Joint, MortiseTenon
from woodwright.part import Board, SideRef
from woodwright.placement import Position, flush_with
from woodwright.stock import Stock

# Makes the joint of a rail end with a stile edge, at a position along the stile.
CornerJoint = Callable[[SideRef, SideRef, Position], Joint]


def _frame(
    name: str,
    corner: CornerJoint,
    stile_length: float,
    rail_length: float,
    width: float,
    stock: Stock,
) -> tuple[Assembly, list[Board]]:
    """Stiles standing up, rails between them at their top and bottom ends."""
    asm = Assembly(name, root_location=STANDING)
    stile_left = asm.add(Board("stile_left", stock, length=stile_length, width=width))
    stile_right = asm.add(Board("stile_right", stock, length=stile_length, width=width))
    rail_top = asm.add(Board("rail_top", stock, length=rail_length, width=width))
    rail_bottom = asm.add(Board("rail_bottom", stock, length=rail_length, width=width))
    # The stiles face each other with their back and front edges; their
    # right ends are at the top.
    for rail_end, stile_edge, stile_end in [
        (rail_top.left_end, stile_left.back_edge, stile_left.right_end),
        (rail_top.right_end, stile_right.front_edge, stile_right.right_end),
        (rail_bottom.left_end, stile_left.back_edge, stile_left.left_end),
        (rail_bottom.right_end, stile_right.front_edge, stile_right.left_end),
    ]:
        asm.join(corner(rail_end, stile_edge, flush_with(stile_end)))
    return asm, [stile_left, stile_right, rail_top, rail_bottom]


def mortise_tenon_frame(
    stile_length: float = 600,
    rail_length: float = 300,
    width: float = 60,
    shoulder: float = 10,
    stock: Stock = OAK,
) -> Assembly:
    """Two stiles and two rails, the rails tenoned into the stiles at their ends."""

    def corner(rail_end: SideRef, stile_edge: SideRef, position: Position) -> Joint:
        return MortiseTenon(
            tenon=rail_end, mortise=stile_edge, position=position, shoulder=shoulder
        )

    asm, _ = _frame("mortise_tenon_frame", corner, stile_length, rail_length, width, stock)
    return asm


def bridle_frame(
    stile_length: float = 400,
    rail_length: float = 250,
    width: float = 50,
    stock: Stock = OAK,
) -> Assembly:
    """A frame with bridle joints at the corners."""

    def corner(rail_end: SideRef, stile_edge: SideRef, position: Position) -> Joint:
        return Bridle(tenon=rail_end, slot=stile_edge, position=position)

    asm, _ = _frame("bridle_frame", corner, stile_length, rail_length, width, stock)
    return asm


def half_lap_frame(
    stile_length: float = 400,
    rail_length: float = 250,
    width: float = 50,
    stock: Stock = OAK,
) -> Assembly:
    """A frame with half-lap corners."""

    def corner(rail_end: SideRef, stile_edge: SideRef, position: Position) -> Joint:
        return HalfLap(lap=rail_end, socket=stile_edge, position=position)

    asm, _ = _frame("half_lap_frame", corner, stile_length, rail_length, width, stock)
    return asm


def frame_and_panel(
    stile_length: float = 600,
    rail_length: float = 300,
    width: float = 60,
    shoulder: float = 10,
    stock: Stock = OAK,
    panel_stock: Stock = THIN_OAK,
) -> Assembly:
    """A mortise-and-tenon frame with a panel in grooves along its inside edges.

    The panel's design size is the opening of the frame; the grooves add to it.
    """

    def corner(rail_end: SideRef, stile_edge: SideRef, position: Position) -> Joint:
        return MortiseTenon(
            tenon=rail_end, mortise=stile_edge, position=position, shoulder=shoulder
        )

    asm, (stile_left, stile_right, rail_top, rail_bottom) = _frame(
        "frame_and_panel", corner, stile_length, rail_length, width, stock
    )
    panel = asm.add(Board("panel", panel_stock, length=stile_length - 2 * width, width=rail_length))
    for groove, edge in [
        (stile_left.back_edge, panel.front_edge),
        (stile_right.front_edge, panel.back_edge),
        (rail_top.back_edge, panel.right_end),
        (rail_bottom.front_edge, panel.left_end),
    ]:
        asm.join(GrooveJoint(groove=groove, edge=edge))
    return asm
