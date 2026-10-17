"""Small practical projects: shop tools, boxes, a shelf, a drawer, a picture frame."""

import build123d as bd

from woodwright.assembly import Assembly
from woodwright.examples._common import OAK, STANDING, THIN_OAK
from woodwright.joints import (
    Bridle,
    Butt,
    DadoJoint,
    MitreCorner,
    MortiseTenon,
    RabbetJoint,
    ThroughDovetail,
)
from woodwright.part import Board
from woodwright.placement import CENTERED, flush_with, offset
from woodwright.stock import Stock

SQUARE_STOCK = Stock.board(thickness=24, species="oak")
BEECH = Stock.board(thickness=60, species="beech")
ASH = Stock.board(thickness=24, species="ash")
THICK_OAK = Stock.board(thickness=30, species="oak")

# A board standing up with its length along X and its width up (Z), its
# reference face towards the viewer (-Y): the front of a box or a drawer.
FRONT = bd.Location(bd.Plane((0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0)))
# The side of a case standing up, its length up (Z), its reference face outside (-X).
CASE_SIDE = bd.Location(bd.Plane((0, 0, 0), x_dir=(0, 0, 1), z_dir=(-1, 0, 0)))


def try_square(
    stock_length: float = 150,
    stock_width: float = 40,
    blade_length: float = 250,
    blade_width: float = 30,
    stock: Stock = SQUARE_STOCK,
) -> Assembly:
    """A try square: a thin blade in a bridle slot at the end of a thick stock.

    The blade is as thin as the slot (a third of the stock's thickness), so
    it goes in whole, without cheeks, centered in the stock's thickness.
    """
    asm = Assembly("try_square", root_location=STANDING)
    handle = asm.add(Board("stock", stock, length=stock_length, width=stock_width))
    blade_stock = Stock.board(thickness=stock.thickness / 3, species=stock.species)
    blade = asm.add(Board("blade", blade_stock, length=blade_length, width=blade_width))
    asm.join(
        Bridle(
            tenon=blade.left_end,
            slot=handle.back_edge,
            position=flush_with(handle.right_end),
            tenon_thickness=blade_stock.thickness,
            across=CENTERED,
        )
    )
    return asm


def mallet(
    head_length: float = 130,
    head_width: float = 70,
    handle_length: float = 300,
    handle_width: float = 32,
    head_stock: Stock = BEECH,
    handle_stock: Stock = ASH,
) -> Assembly:
    """A mallet: a long handle tenoned through the middle of a big head."""
    asm = Assembly("mallet")
    head = asm.add(Board("head", head_stock, length=head_length, width=head_width))
    handle = asm.add(Board("handle", handle_stock, length=handle_length, width=handle_width))
    asm.join(
        MortiseTenon(
            tenon=handle.right_end,
            mortise=head.front_edge,
            tenon_length=head_width,
            tenon_thickness=12,
            shoulder=4,
            across=CENTERED,
        )
    )
    return asm


def shooting_board(
    length: float = 450,
    width: float = 250,
    stop_width: float = 40,
    stop_from_end: float = 30,
    stock: Stock = OAK,
    stop_stock: Stock = THICK_OAK,
) -> Assembly:
    """A base board with a stop block across it, housed in a dado near one end."""
    asm = Assembly("shooting_board")
    base = asm.add(Board("base", stock, length=length, width=width))
    stop = asm.add(Board("stop", stop_stock, length=width, width=stop_width))
    asm.join(
        DadoJoint(
            dado=base.top_face,
            end=stop.front_edge,
            position=offset(stop_from_end, base.right_end),
            # The stop lies across the base: its end flush with the base's front edge.
            flush=(base.front_edge, stop.left_end),
        )
    )
    return asm


def butt_box(
    length: float = 300,
    depth: float = 200,
    height: float = 100,
    stock: Stock = THIN_OAK,
) -> Assembly:
    """An open box: four walls butt-jointed at the corners on a bottom; outside sizes."""
    t = stock.thickness
    asm = Assembly("butt_box", root_location=FRONT)
    wall_height = height - t
    front = asm.add(Board("front", stock, length=length, width=wall_height))
    back = asm.add(Board("back", stock, length=length, width=wall_height))
    left = asm.add(Board("left", stock, length=depth - 2 * t, width=wall_height))
    right = asm.add(Board("right", stock, length=depth - 2 * t, width=wall_height))
    bottom = asm.add(Board("bottom", stock, length=length, width=depth))
    # The sides between the front and the back, their bottom (front) edges level.
    asm.join(Butt(front.bottom_face, left.left_end, position=flush_with(front.left_end)))
    asm.join(Butt(front.bottom_face, right.right_end, position=flush_with(front.right_end)))
    asm.join(Butt(back.bottom_face, left.right_end, position=flush_with(back.right_end)))
    asm.join(Butt(back.bottom_face, right.left_end, position=flush_with(back.left_end)))
    # The walls stand on the bottom, flush with its sides.
    asm.join(Butt(front.front_edge, bottom.top_face, position=flush_with(front.left_end)))
    # The back is a mirror image of the front (reference face outside), so
    # the bottom's back edge faces the same way as the back's reference face.
    asm.join(
        Butt(
            back.front_edge,
            bottom.top_face,
            position=flush_with(back.right_end),
            flush=(back.ref_face, bottom.back_edge),
        )
    )
    return asm


def bookshelf(
    height: float = 800,
    width: float = 500,
    depth: float = 250,
    stock: Stock = OAK,
) -> Assembly:
    """Two sides with a top and a bottom in rabbets and a middle shelf in dados.

    Outside sizes; the shelves' design length is between the sides.
    """
    t = stock.thickness
    asm = Assembly("bookshelf", root_location=CASE_SIDE)
    left = asm.add(Board("left", stock, length=height, width=depth))
    right = asm.add(Board("right", stock, length=height, width=depth))
    top = asm.add(Board("top", stock, length=width - 2 * t, width=depth))
    bottom = asm.add(Board("bottom", stock, length=width - 2 * t, width=depth))
    shelf = asm.add(Board("shelf", stock, length=width - 2 * t, width=depth))
    # Both sides have their reference faces outside and reference edges at
    # the front, so they are mirror images: the left one has its right end
    # up, the right one its left end.
    asm.join(RabbetJoint(rabbet=left.bottom_face, end=top.left_end, at=left.right_end))
    asm.join(RabbetJoint(rabbet=right.bottom_face, end=top.right_end, at=right.left_end))
    asm.join(RabbetJoint(rabbet=left.bottom_face, end=bottom.left_end, at=left.left_end))
    asm.join(RabbetJoint(rabbet=right.bottom_face, end=bottom.right_end, at=right.right_end))
    for side, end, side_top in [
        (left, shelf.left_end, left.right_end),
        (right, shelf.right_end, right.left_end),
    ]:
        asm.join(DadoJoint(dado=side.bottom_face, end=end, position=offset(height / 2, side_top)))
    return asm


def dovetail_drawer(
    width: float = 400,
    depth: float = 500,
    height: float = 150,
    stock: Stock = OAK,
) -> Assembly:
    """A drawer box with through dovetails at all four corners (no bottom); outside sizes.

    The front and the back have pins at both ends, the sides tails at both
    ends, so the front can't be pulled off. All boards have their reference
    faces outside and reference edges at the bottom; the mirror images (the
    back of the front, the right side of the left one) have their ends swapped.
    """
    t = stock.thickness
    asm = Assembly("dovetail_drawer", root_location=FRONT)
    front = asm.add(Board("front", stock, length=width - 2 * t, width=height))
    back = asm.add(Board("back", stock, length=width - 2 * t, width=height))
    left = asm.add(Board("left", stock, length=depth - 2 * t, width=height))
    right = asm.add(Board("right", stock, length=depth - 2 * t, width=height))
    for tails, pins in [
        (left.right_end, front.left_end),
        (right.left_end, front.right_end),
        (left.left_end, back.right_end),
        (right.right_end, back.left_end),
    ]:
        asm.join(ThroughDovetail(tails=tails, pins=pins, tail_count=3))
    return asm


def picture_frame(
    width: float = 400,
    height: float = 300,
    member_width: float = 40,
    stock: Stock = OAK,
) -> Assembly:
    """A frame mitred at all four corners; outside sizes."""
    asm = Assembly("picture_frame", root_location=STANDING)
    left = asm.add(Board("left", stock, length=height, width=member_width))
    top = asm.add(Board("top", stock, length=width, width=member_width))
    right = asm.add(Board("right", stock, length=height, width=member_width))
    bottom = asm.add(Board("bottom", stock, length=width, width=member_width))
    members = [left, top, right, bottom]
    for a, b in zip(members, members[1:] + members[:1], strict=True):
        asm.join(MitreCorner(a.right_end, b.left_end, a.back_edge, b.back_edge))
    return asm
