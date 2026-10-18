"""Frames of two stiles and two rails, frames with a panel, a shoji lattice."""

from collections.abc import Callable

from woodwright.assembly import Assembly
from woodwright.examples._common import OAK, STANDING, THIN_OAK
from woodwright.joints import (
    Bridle,
    Butt,
    CrossLap,
    GrooveJoint,
    HalfLap,
    Joint,
    MortiseTenon,
    TongueAndGroove,
)
from woodwright.part import Board, SideRef
from woodwright.placement import CENTERED, Position, flush_with, offset
from woodwright.stock import Stock

# Kumiko: thin bars, much deeper (across the lattice) than wide.
KUMIKO = Stock.board(thickness=20, species="oak")

# Makes the joint of a rail end with a stile edge, at a position along the
# stile; the last side is the rail's outer edge.
CornerJoint = Callable[[SideRef, SideRef, Position, SideRef], Joint]


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
    # right ends are at the top. The rails' outer edges are their front edge
    # (top rail) and back edge (bottom rail).
    for rail_end, stile_edge, stile_end, outer in [
        (rail_top.left_end, stile_left.back_edge, stile_left.right_end, rail_top.front_edge),
        (rail_top.right_end, stile_right.front_edge, stile_right.right_end, rail_top.front_edge),
        (rail_bottom.left_end, stile_left.back_edge, stile_left.left_end, rail_bottom.back_edge),
        (
            rail_bottom.right_end,
            stile_right.front_edge,
            stile_right.left_end,
            rail_bottom.back_edge,
        ),
    ]:
        asm.join(corner(rail_end, stile_edge, flush_with(stile_end), outer))
    return asm, [stile_left, stile_right, rail_top, rail_bottom]


def mortise_tenon_frame(
    stile_length: float = 600,
    rail_length: float = 300,
    width: float = 60,
    shoulder: float = 10,
    stock: Stock = OAK,
) -> Assembly:
    """Two stiles and two rails, the rails tenoned into the stiles at their ends."""

    def corner(rail_end: SideRef, stile_edge: SideRef, position: Position, outer: SideRef) -> Joint:
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

    def corner(rail_end: SideRef, stile_edge: SideRef, position: Position, outer: SideRef) -> Joint:
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

    def corner(rail_end: SideRef, stile_edge: SideRef, position: Position, outer: SideRef) -> Joint:
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
    The grooves run through the stiles, so the tenons are as thick as the
    grooves are wide and have haunches filling the grooves out to the ends.
    """

    def corner(rail_end: SideRef, stile_edge: SideRef, position: Position, outer: SideRef) -> Joint:
        return MortiseTenon(
            tenon=rail_end,
            mortise=stile_edge,
            position=position,
            shoulder=shoulder,
            tenon_thickness=panel_stock.thickness,
            haunch=outer,
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


def butt_frame_and_panel(
    stile_length: float = 500,
    rail_length: float = 300,
    width: float = 60,
    tongue_length: float = 10,
    stock: Stock = OAK,
    panel_stock: Stock = THIN_OAK,
) -> Assembly:
    """A frame butt-joined at the corners, a panel tongued on all four edges
    into grooves along its inside edges.

    The panel's design size is the opening of the frame, the tongues add to
    it; it is centered in the frame's thickness. The grooves run through,
    as cut on a table saw: those in the rails into the ones in the stiles,
    which show at the stiles' ends (stopped grooves would hide them). The
    glued corners hold little (end grain on long grain): a frame for a
    light panel, or one to be screwed or dowelled (not modelled).
    """

    def corner(rail_end: SideRef, stile_edge: SideRef, position: Position, outer: SideRef) -> Joint:
        return Butt(stile_edge, rail_end, position=position)

    asm, (stile_left, stile_right, rail_top, rail_bottom) = _frame(
        "butt_frame_and_panel", corner, stile_length, rail_length, width, stock
    )
    panel = asm.add(Board("panel", panel_stock, length=stile_length - 2 * width, width=rail_length))
    for groove, edge in [
        (stile_left.back_edge, panel.front_edge),
        (stile_right.front_edge, panel.back_edge),
        (rail_top.back_edge, panel.right_end),
        (rail_bottom.front_edge, panel.left_end),
    ]:
        asm.join(
            TongueAndGroove(
                tongue=edge,
                groove=groove,
                tongue_length=tongue_length,
                across=CENTERED,
            )
        )
    return asm


def shoji_frame(
    width: float = 200,
    height: float = 300,
    bar_width: float = 5,
    overhang: float = 20,
    stock: Stock = KUMIKO,
) -> Assembly:
    """A small shoji lattice of three vertical and three horizontal bars,
    crossing in nine cross laps; outside sizes.

    The bars reach `overhang` beyond the outer ones. They are `bar_width`
    wide in the lattice and the stock thick across it; each lap takes half
    of that. Where they cross, the vertical bars keep their front halves and
    the horizontal ones their back halves (the reference faces are at the back).
    """
    asm = Assembly("shoji_frame", root_location=STANDING)
    verticals = [asm.add(Board(f"vertical_{i + 1}", stock, height, bar_width)) for i in range(3)]
    horizontals = [asm.add(Board(f"horizontal_{i + 1}", stock, width, bar_width)) for i in range(3)]

    def starts(length: float) -> list[float]:
        """Where the three bars crossing a bar of this length start along it."""
        return [overhang, (length - bar_width) / 2, length - overhang - bar_width]

    # The horizontal bars run to the right, so their left ends cross each
    # vertical bar from its back edge.
    for vertical, x in zip(verticals, starts(width), strict=True):
        for horizontal, y in zip(horizontals, starts(height), strict=True):
            asm.join(
                CrossLap(
                    vertical.back_edge,
                    horizontal.left_end,
                    position=offset(y, vertical.left_end),
                    overhang=x,
                )
            )
    return asm
