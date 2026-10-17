"""Small practical projects: shop tools, boxes, a shelf, a drawer, a picture frame."""

from woodwright import rules
from woodwright.assembly import Assembly
from woodwright.examples._common import BOX_FRONT, CASE_SIDE, OAK, STANDING, THIN_OAK
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

LEG_STOCK = Stock.board(thickness=45, species="oak")


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
    asm = Assembly("butt_box", root_location=BOX_FRONT)
    wall_height = height - t
    front = asm.add(Board("front", stock, length=length, width=wall_height))
    # The back and the right side are mirror images of the front and the
    # left side, all with their reference faces outside.
    back = asm.add(Board("back", stock, length=length, width=wall_height, mirror=True))
    left = asm.add(Board("left", stock, length=depth - 2 * t, width=wall_height))
    right = asm.add(Board("right", stock, length=depth - 2 * t, width=wall_height, mirror=True))
    bottom = asm.add(Board("bottom", stock, length=length, width=depth))
    # The sides between the front and the back, their bottom (front) edges level.
    for side, front_end, back_end in [
        (left, front.left_end, back.left_end),
        (right, front.right_end, back.right_end),
    ]:
        asm.join(Butt(front.bottom_face, side.left_end, position=flush_with(front_end)))
        asm.join(Butt(back.bottom_face, side.right_end, position=flush_with(back_end)))
    # The walls stand on the bottom, flush with its sides. The back faces
    # the other way than the front, so its reference face (outside) is flush
    # with the bottom's back edge.
    asm.join(Butt(front.front_edge, bottom.top_face, position=flush_with(front.left_end)))
    asm.join(
        Butt(
            back.front_edge,
            bottom.top_face,
            position=flush_with(back.left_end),
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
    # Both sides have their reference faces outside and reference edges at
    # the front, so they are mirror images; both have their right end up.
    left = asm.add(Board("left", stock, length=height, width=depth))
    right = asm.add(Board("right", stock, length=height, width=depth, mirror=True))
    top = asm.add(Board("top", stock, length=width - 2 * t, width=depth))
    bottom = asm.add(Board("bottom", stock, length=width - 2 * t, width=depth))
    shelf = asm.add(Board("shelf", stock, length=width - 2 * t, width=depth))
    for side, top_end, bottom_end, shelf_end in [
        (left, top.left_end, bottom.left_end, shelf.left_end),
        (right, top.right_end, bottom.right_end, shelf.right_end),
    ]:
        asm.join(RabbetJoint(rabbet=side.bottom_face, end=top_end, at=side.right_end))
        asm.join(RabbetJoint(rabbet=side.bottom_face, end=bottom_end, at=side.left_end))
        asm.join(
            DadoJoint(
                dado=side.bottom_face, end=shelf_end, position=offset(height / 2, side.right_end)
            )
        )
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
    faces outside and reference edges at the bottom; the back and the right
    side are mirror images of the front and the left side.
    """
    t = stock.thickness
    asm = Assembly("dovetail_drawer", root_location=BOX_FRONT)
    front = asm.add(Board("front", stock, length=width - 2 * t, width=height))
    back = asm.add(Board("back", stock, length=width - 2 * t, width=height, mirror=True))
    left = asm.add(Board("left", stock, length=depth - 2 * t, width=height))
    right = asm.add(Board("right", stock, length=depth - 2 * t, width=height, mirror=True))
    # The sides' right ends are at the front.
    for side, front_end, back_end in [
        (left, front.left_end, back.left_end),
        (right, front.right_end, back.right_end),
    ]:
        asm.join(ThroughDovetail(tails=side.right_end, pins=front_end, tail_count=3))
        asm.join(ThroughDovetail(tails=side.left_end, pins=back_end, tail_count=3))
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


def table_frame(
    width: float = 800,
    depth: float = 500,
    height: float = 700,
    apron_width: float = 100,
    setback: float = 3,
    leg_stock: Stock = LEG_STOCK,
    stock: Stock = OAK,
) -> Assembly:
    """Four legs and four aprons tenoned into them, without a top; outside sizes.

    At each leg two tenons meet from adjacent sides, so they are mitred and
    meet on the leg's diagonal. Each apron goes from the back edge of one
    leg to the top face of the next one, so the legs are all the same,
    turned by 90 degrees around the table.
    """
    leg_width = leg_stock.thickness
    tenon = rules.tenon_thickness(stock.thickness)
    tenon_length = leg_width - setback - (stock.thickness - tenon) / 2
    # The front left leg stands at the origin, its outside sides (bottom face,
    # front edge) to the front and to the left.
    asm = Assembly("table_frame", root_location=STANDING)
    names = ["front_left", "front_right", "back_right", "back_left"]
    legs = [
        asm.add(Board(f"leg_{name}", leg_stock, length=height, width=leg_width)) for name in names
    ]
    aprons = [
        asm.add(Board(f"apron_{name}", stock, length=length - 2 * leg_width, width=apron_width))
        for name, length in [("front", width), ("right", depth), ("back", width), ("left", depth)]
    ]
    for i, apron in enumerate(aprons):
        this_leg, next_leg = legs[i], legs[(i + 1) % 4]
        for end, leg, mortise, outside in [
            (apron.left_end, this_leg, this_leg.back_edge, this_leg.bottom_face),
            (apron.right_end, next_leg, next_leg.top_face, next_leg.front_edge),
        ]:
            asm.join(
                MortiseTenon(
                    tenon=end,
                    mortise=mortise,
                    position=flush_with(leg.right_end),
                    flush=(outside, apron.ref_face),
                    across=offset(setback),
                    tenon_thickness=tenon,
                    tenon_length=tenon_length,
                    shoulder=10,
                    mitre=apron.bottom_face,
                )
            )
    return asm
