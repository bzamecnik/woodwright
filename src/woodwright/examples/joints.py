"""Joints of two boards."""

import itertools

import build123d as bd

from woodwright.assembly import Assembly
from woodwright.examples._common import OAK, STANDING, THIN_OAK
from woodwright.joints import (
    Bridle,
    Butt,
    CrossLap,
    DadoJoint,
    GrooveJoint,
    HalfLap,
    MitreCorner,
    MitreSplice,
    MortiseTenon,
    RabbetJoint,
    SlidingDovetail,
    ThroughDovetail,
    TongueAndGroove,
)
from woodwright.part import Board
from woodwright.placement import CENTERED, flush_with, offset
from woodwright.stock import Stock

THICK_OAK = Stock.board(thickness=30, species="oak")

# The side of a carcase stands up, its reference face outside at x = 0.
CARCASE_SIDE = bd.Location(bd.Plane((0, 0, 0), x_dir=(0, 0, 1), z_dir=(-1, 0, 0)))


# --- Butt joints ------------------------------------------------------------


def butt_panel(
    length: float = 500, width: float = 150, count: int = 3, stock: Stock = OAK
) -> Assembly:
    """Boards glued edge to edge into a panel."""
    asm = Assembly("butt_panel")
    boards = [
        asm.add(Board(f"board_{i + 1}", stock, length=length, width=width)) for i in range(count)
    ]
    for a, b in itertools.pairwise(boards):
        asm.join(Butt(a.back_edge, b.front_edge))
    return asm


def laminated_leg(length: float = 450, width: float = 40, stock: Stock = OAK) -> Assembly:
    """Two boards glued face to face into a thicker leg."""
    asm = Assembly("laminated_leg")
    a = asm.add(Board("a", stock, length=length, width=width))
    b = asm.add(Board("b", stock, length=length, width=width))
    asm.join(Butt(a.bottom_face, b.top_face))
    return asm


def butt_corner(
    side_height: float = 400, top_length: float = 500, depth: float = 200, stock: Stock = OAK
) -> Assembly:
    """A carcase corner: the end of the top glued against the inside of the side.

    The top's length is between the sides, the side's height is overall.
    """
    asm = Assembly("butt_corner", root_location=CARCASE_SIDE)
    side = asm.add(Board("side", stock, length=side_height, width=depth))
    top = asm.add(Board("top", stock, length=top_length - stock.thickness, width=depth))
    asm.join(Butt(side.bottom_face, top.left_end, position=flush_with(side.right_end)))
    return asm


# --- Housings: dado, rabbet, groove -------------------------------------------


def dado_shelf(
    side_height: float = 400,
    shelf_length: float = 300,
    depth: float = 200,
    shelf_height: float = 150,
    stock: Stock = OAK,
) -> Assembly:
    """A shelf housed in a dado in the side, `shelf_height` below its top end."""
    asm = Assembly("dado_shelf", root_location=CARCASE_SIDE)
    side = asm.add(Board("side", stock, length=side_height, width=depth))
    shelf = asm.add(Board("shelf", stock, length=shelf_length, width=depth))
    asm.join(
        DadoJoint(
            dado=side.bottom_face, end=shelf.left_end, position=offset(shelf_height, side.right_end)
        )
    )
    return asm


def rabbet_corner(
    side_height: float = 400, top_length: float = 500, depth: float = 200, stock: Stock = OAK
) -> Assembly:
    """A carcase corner: the end of the top in a rabbet at the top end of the side.

    The top's length is between the sides, the side's height is overall.
    """
    asm = Assembly("rabbet_corner", root_location=CARCASE_SIDE)
    side = asm.add(Board("side", stock, length=side_height, width=depth))
    top = asm.add(Board("top", stock, length=top_length - stock.thickness, width=depth))
    asm.join(RabbetJoint(rabbet=side.bottom_face, end=top.left_end, at=side.right_end))
    return asm


def sliding_dovetail_shelf(
    side_height: float = 400,
    shelf_length: float = 300,
    depth: float = 200,
    shelf_height: float = 150,
    stock: Stock = OAK,
) -> Assembly:
    """A shelf with a dovetail tongue slid into a dovetail socket across the side.

    Like the dado shelf, but the shelf can't be pulled out of the side.
    """
    asm = Assembly("sliding_dovetail_shelf", root_location=CARCASE_SIDE)
    side = asm.add(Board("side", stock, length=side_height, width=depth))
    shelf = asm.add(Board("shelf", stock, length=shelf_length, width=depth))
    asm.join(
        SlidingDovetail(
            socket=side.bottom_face,
            end=shelf.left_end,
            position=offset(shelf_height, side.right_end),
        )
    )
    return asm


def interlocking_rabbet_corner(
    side_height: float = 400, top_length: float = 500, depth: float = 200, stock: Stock = OAK
) -> Assembly:
    """A carcase corner with two interlocking rabbets: a lip of the top in a rabbet of the side.

    The side's outer lip covers the top's end grain. The top's length is
    between the sides, the side's height is overall.
    """
    asm = Assembly("interlocking_rabbet_corner", root_location=CARCASE_SIDE)
    side = asm.add(Board("side", stock, length=side_height, width=depth))
    top = asm.add(Board("top", stock, length=top_length - stock.thickness, width=depth))
    asm.join(
        RabbetJoint(
            rabbet=side.bottom_face,
            end=top.left_end,
            at=side.right_end,
            lap=stock.thickness / 2,
        )
    )
    return asm


def panel_in_groove(
    length: float = 400,
    rail_width: float = 60,
    panel_width: float = 200,
    panel_stock: Stock = THIN_OAK,
    stock: Stock = OAK,
) -> Assembly:
    """A thin panel with its edge in a groove along a rail, centered in its thickness."""
    asm = Assembly("panel_in_groove")
    rail = asm.add(Board("rail", stock, length=length, width=rail_width))
    panel = asm.add(Board("panel", panel_stock, length=length, width=panel_width))
    asm.join(GrooveJoint(groove=rail.back_edge, edge=panel.front_edge))
    return asm


def tongue_and_groove_panel(
    length: float = 500, width: float = 150, count: int = 3, stock: Stock = OAK
) -> Assembly:
    """Boards edge to edge, a tongue along each in a groove along the next one."""
    asm = Assembly("tongue_and_groove_panel")
    boards = [
        asm.add(Board(f"board_{i + 1}", stock, length=length, width=width)) for i in range(count)
    ]
    for a, b in itertools.pairwise(boards):
        asm.join(TongueAndGroove(tongue=b.front_edge, groove=a.back_edge))
    return asm


# --- Laps, bridles, mortise and tenon -------------------------------------------


def half_lap_corner(
    stile_length: float = 300, rail_length: float = 200, width: float = 40, stock: Stock = OAK
) -> Assembly:
    """An L-shaped half-lap corner: a lap on the rail, an end rabbet on the stile."""
    asm = Assembly("half_lap_corner", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    asm.join(
        HalfLap(lap=rail.left_end, socket=stile.back_edge, position=flush_with(stile.right_end))
    )
    return asm


def half_lap_t(
    stile_length: float = 300, rail_length: float = 200, width: float = 40, stock: Stock = OAK
) -> Assembly:
    """A T-shaped half lap: a lap on the end of the rail, a dado across the stile."""
    asm = Assembly("half_lap_t", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    asm.join(HalfLap(lap=rail.left_end, socket=stile.back_edge))
    return asm


def bridle_corner(
    stile_length: float = 300,
    rail_length: float = 200,
    stile_width: float = 50,
    rail_width: float = 30,
    stock: Stock = OAK,
) -> Assembly:
    """An L-shaped bridle joint: a tenon over the whole rail in a slot in the stile's end.

    The rail may be narrower than the stile: the slot is as deep as the rail
    is wide, the tenon as long as the stile is wide.
    """
    asm = Assembly("bridle_corner", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=stile_width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=rail_width))
    asm.join(
        Bridle(tenon=rail.left_end, slot=stile.back_edge, position=flush_with(stile.right_end))
    )
    return asm


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
    asm.join(MortiseTenon(tenon=rail.left_end, mortise=stile.back_edge))
    return asm


def through_mortise_tenon(
    stile_length: float = 600,
    rail_length: float = 300,
    width: float = 60,
    stock: Stock = OAK,
) -> Assembly:
    """A rail tenoned through the stile: the tenon is as long as the stile is wide."""
    asm = Assembly("through_mortise_tenon", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    asm.join(MortiseTenon(tenon=rail.left_end, mortise=stile.back_edge, tenon_length=width))
    return asm


def mortise_tenon_thin_rail(
    stile_length: float = 600,
    rail_length: float = 300,
    width: float = 60,
    stock: Stock = THICK_OAK,
    rail_stock: Stock = OAK,
) -> Assembly:
    """A rail thinner than the stile, centered on it across the thickness."""
    asm = Assembly("mortise_tenon_thin_rail", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", rail_stock, length=rail_length, width=width))
    asm.join(MortiseTenon(tenon=rail.left_end, mortise=stile.back_edge, across=CENTERED))
    return asm


# --- Dovetails --------------------------------------------------------------


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
    asm = Assembly("dovetail_corner", root_location=CARCASE_SIDE)
    side = asm.add(Board("side", stock, length=side_height - stock.thickness, width=depth))
    top = asm.add(Board("top", stock, length=top_length - stock.thickness, width=depth))
    asm.join(ThroughDovetail(tails=top.left_end, pins=side.right_end, tail_count=tail_count))
    return asm


# --- More corners -------------------------------------------------------------


def butt_frame_corner(
    stile_length: float = 300, rail_length: float = 200, width: float = 40, stock: Stock = OAK
) -> Assembly:
    """An L-shaped corner of a frame: the end of the rail glued to the edge of the stile."""
    asm = Assembly("butt_frame_corner", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    asm.join(Butt(stile.back_edge, rail.left_end, position=flush_with(stile.right_end)))
    return asm


def mitre_corner(
    stile_length: float = 300, rail_length: float = 200, width: float = 40, stock: Stock = OAK
) -> Assembly:
    """A picture frame corner: both ends mitred across the face, lengths to the outside."""
    asm = Assembly("mitre_corner", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    asm.join(MitreCorner(stile.right_end, rail.left_end, stile.back_edge, rail.back_edge))
    return asm


def edge_mitre_corner(
    side_height: float = 400, top_length: float = 500, depth: float = 200, stock: Stock = OAK
) -> Assembly:
    """A carcase corner mitred across the edges, so no end grain shows; outside lengths."""
    asm = Assembly("edge_mitre_corner", root_location=CARCASE_SIDE)
    side = asm.add(Board("side", stock, length=side_height, width=depth))
    top = asm.add(Board("top", stock, length=top_length, width=depth))
    asm.join(MitreCorner(side.right_end, top.left_end, side.bottom_face, top.bottom_face))
    return asm


def mitre_splice(
    length: float = 300, width: float = 40, angle: float = 45, stock: Stock = OAK
) -> Assembly:
    """Two stiles end to end, lengthened by a mitre across the face."""
    asm = Assembly("mitre_splice", root_location=STANDING)
    a = asm.add(Board("a", stock, length=length, width=width))
    b = asm.add(Board("b", stock, length=length, width=width))
    asm.join(MitreSplice(a.right_end, b.left_end, short=a.back_edge, angle=angle))
    return asm


def cross_lap(
    length_a: float = 300, length_b: float = 200, width: float = 40, stock: Stock = OAK
) -> Assembly:
    """Two boards crossing in their middles, each with a dado half its thickness deep."""
    asm = Assembly("cross_lap")
    a = asm.add(Board("a", stock, length=length_a, width=width))
    b = asm.add(Board("b", stock, length=length_b, width=width))
    asm.join(CrossLap(a.back_edge, b.left_end))
    return asm
