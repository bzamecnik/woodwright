"""Joints of two boards."""

import build123d as bd

from woodwright.assembly import Assembly
from woodwright.examples._common import OAK, STANDING
from woodwright.joints import MortiseTenon, ThroughDovetail
from woodwright.part import Board
from woodwright.placement import Offset
from woodwright.stock import Stock


def mortise_tenon(
    stile_length: float = 600,
    rail_length: float = 300,
    width: float = 60,
    stock: Stock = OAK,
) -> Assembly:
    """A rail tenoned into the back edge of a stile, centered along it (T-joint)."""
    asm = Assembly("mortise_tenon", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    asm.join(MortiseTenon(tenon=rail.left_end, mortise=stile.back_edge, tenon_length=width))
    return asm


def bridle_corner(
    stile_length: float = 300,
    rail_length: float = 200,
    width: float = 40,
    stock: Stock = OAK,
) -> Assembly:
    """An L-shaped bridle joint: a tenon as wide as the rail in an open-ended slot.

    So far it only works for stock of the same thickness.
    """
    asm = Assembly("bridle_corner")
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    asm.join(
        MortiseTenon(
            tenon=rail.left_end,
            mortise=stile.front_edge,
            position=Offset(0),
            tenon_length=rail.width,
            shoulder=0,
        )
    )
    return asm


def tongue_and_groove_panel(
    length: float = 500,
    width: float = 150,
    tongue_length: float = 10,
    stock: Stock = OAK,
) -> Assembly:
    """Two boards edge to edge, a tongue along one in a groove along the other."""
    asm = Assembly("tongue_and_groove_panel")
    board_1 = asm.add(Board("board_1", stock, length=length, width=width))
    board_2 = asm.add(Board("board_2", stock, length=length, width=width))
    asm.join(
        MortiseTenon(
            tenon=board_1.back_edge,
            mortise=board_2.front_edge,
            tenon_length=tongue_length,
            shoulder=0,
            clearance=0,
        )
    )
    return asm


def dovetail_corner(
    side_height: float = 400,
    top_length: float = 500,
    depth: float = 200,
    tail_count: int = 4,
    stock: Stock = OAK,
) -> Assembly:
    """A through-dovetail corner of a carcase: tails on the top, pins on the side.

    The heights and lengths are outside dimensions: the boards reach through
    each other, so their design lengths are shorter by the other board's
    thickness, which the joint adds back as an allowance.
    """
    # The side stands up, its reference face outside at x = 0.
    root_location = bd.Location(bd.Plane((0, 0, 0), x_dir=(0, 0, 1), z_dir=(-1, 0, 0)))
    asm = Assembly("dovetail_corner", root_location=root_location)
    side = asm.add(Board("side", stock, length=side_height - stock.thickness, width=depth))
    top = asm.add(Board("top", stock, length=top_length - stock.thickness, width=depth))
    asm.join(ThroughDovetail(tails=top.left_end, pins=side.right_end, tail_count=tail_count))
    return asm
