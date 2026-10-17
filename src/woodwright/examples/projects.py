"""Small practical projects: shop tools, boxes, a shelf, a drawer, a picture frame."""

import math

from woodwright import rules
from woodwright.assembly import Assembly
from woodwright.cuts import Groove, Tongue
from woodwright.examples._common import BOX_FRONT, CASE_SIDE, OAK, SIDE_OAK, STANDING, THIN_OAK
from woodwright.joints import (
    Bridle,
    Butt,
    DadoJoint,
    HalfBlindDovetail,
    MitreCorner,
    MortiseTenon,
    RabbetJoint,
    ThroughDovetail,
    TongueAndGroove,
)
from woodwright.part import Board, SideRef
from woodwright.placement import CENTERED, Position, flush_with, offset
from woodwright.stock import Stock

SQUARE_STOCK = Stock.board(thickness=24, species="oak")
BEECH = Stock.board(thickness=60, species="beech")
ASH = Stock.board(thickness=24, species="ash")
THICK_OAK = Stock.board(thickness=30, species="oak")

LEG_STOCK = Stock.board(thickness=45, species="oak")
TABLE_LEG_STOCK = Stock.board(thickness=60, species="oak")


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


def drawer(
    width: float = 400,
    depth: float = 450,
    height: float = 150,
    groove_height: float = 10,
    groove_width: float = 6,
    groove_depth: float = 5,
    stock: Stock = OAK,
    side_stock: Stock = SIDE_OAK,
    bottom_stock: Stock = THIN_OAK,
) -> Assembly:
    """A classic drawer with a bottom; outside sizes.

    The front has half-blind dovetails, so the tails don't show from the
    front; its bottom half pins are narrow, so that the groove runs through
    the bottom tails and is hidden. The back is through dovetailed. The bottom slides in grooves in
    the sides and the front, under the back, which is narrower and sits on
    it. The bottom's edges are rabbeted on its underside to fit the grooves,
    its top flush with their tops; its grain runs from side to side, so it
    moves towards the back. The groove's lower wall is `groove_height` above
    the bottom edges. The back and the right side are mirror images of the
    front and the left side, all with their reference faces outside.
    """
    s, b = side_stock.thickness, bottom_stock.thickness
    side_length = depth - stock.thickness - s
    asm = Assembly("drawer", root_location=BOX_FRONT)
    front = asm.add(Board("front", stock, length=width - 2 * s, width=height))
    back_height = height - groove_height - groove_width
    back = asm.add(Board("back", side_stock, length=width - 2 * s, width=back_height, mirror=True))
    left = asm.add(Board("left", side_stock, length=side_length, width=height))
    right = asm.add(Board("right", side_stock, length=side_length, width=height, mirror=True))
    bottom = asm.add(Board("bottom", bottom_stock, length=width - 2 * s, width=side_length + s))

    def in_groove(tongue: SideRef, groove: SideRef, position: Position) -> TongueAndGroove:
        """The bottom's edge or end in a groove in the inside face of the front or a side."""
        return TongueAndGroove(
            tongue=tongue,
            groove=groove,
            tongue_thickness=groove_width,
            tongue_length=groove_depth,
            tongue_offset=0,
            position=position,
            flush=(groove.part.ref_edge, bottom.bottom_face),
            across=offset(groove_height + groove_width - b),
        )

    # The groove runs out of the front's ends: it must pass through the bottom
    # tail, not through the half pin below it, which shows on the side. The
    # half pin is narrowest at the lap and widens by the slope towards the
    # inside (by 1:7); the groove stays at least 2 mm above it.
    socket_depth = stock.thickness - rules.dovetail_lap(stock.thickness)
    half_pin = math.floor(groove_height - socket_depth / 7 - 2)
    # The sides' right ends are at the front; the back's top edge is flush with theirs.
    for side, front_end, back_end, bottom_end in [
        (left, front.left_end, back.left_end, bottom.left_end),
        (right, front.right_end, back.right_end, bottom.right_end),
    ]:
        asm.join(
            HalfBlindDovetail(
                tails=side.right_end, pins=front_end, tail_count=3, half_pin_width=half_pin
            )
        )
        asm.join(
            ThroughDovetail(
                tails=side.left_end,
                pins=back_end,
                tail_count=2,
                flush=(back.back_edge, side.back_edge),
            )
        )
        asm.join(in_groove(bottom_end, side.bottom_face, flush_with(side.right_end)))
    asm.join(in_groove(bottom.front_edge, front.bottom_face, flush_with(front.left_end)))
    # The back sits on the bottom, which reaches to its outside face.
    asm.join(Butt(bottom.top_face, back.ref_edge, flush=(bottom.back_edge, back.ref_face)))
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


def _table_frame(
    asm: Assembly,
    width: float,
    depth: float,
    height: float,
    apron_width: float,
    setback: float,
    leg_stock: Stock,
    stock: Stock,
    shoulder: float | tuple[float, float] = 10,
    haunch_length: float | None = None,
) -> tuple[list[Board], list[Board]]:
    """Four legs and four aprons with mitred tenons; outside sizes.

    Each apron goes from the back edge of one leg to the top face of the
    next one, so the legs are all the same, turned by 90 degrees around the
    table. The aprons have their reference faces outside and their back
    edges up; with `haunch_length` the tenons get haunches at the top.
    """
    leg_width = leg_stock.thickness
    tenon = rules.tenon_thickness(stock.thickness)
    tenon_length = leg_width - setback - (stock.thickness - tenon) / 2
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
                    shoulder=shoulder,
                    haunch=None if haunch_length is None else apron.back_edge,
                    haunch_length=haunch_length,
                    mitre=apron.bottom_face,
                )
            )
    return legs, aprons


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
    meet on the leg's diagonal.
    """
    # The front left leg stands at the origin, its outside sides (bottom face,
    # front edge) to the front and to the left.
    asm = Assembly("table_frame", root_location=STANDING)
    _table_frame(asm, width, depth, height, apron_width, setback, leg_stock, stock)
    return asm


def table(
    width: float = 1200,
    depth: float = 750,
    height: float = 750,
    overhang: float = 40,
    apron_width: float = 120,
    setback: float = 3,
    buttons: tuple[int, int] = (3, 2),
    leg_stock: Stock = TABLE_LEG_STOCK,
    stock: Stock = OAK,
    top_stock: Stock = THICK_OAK,
) -> Assembly:
    """A table: legs and wide aprons, a solid top held down by buttons; outside sizes.

    `width` and `depth` are those of the frame, the top overhangs it by
    `overhang`. The aprons are wide, so their tenons are set down from the
    top of the legs, with haunches filling the wide shoulders: the legs
    keep their tops whole, and the aprons can't twist. The top is not
    glued: wooden buttons screwed to its underside engage a groove along
    the inside of each apron (`buttons` along the front and back, and along
    the sides), so it can move across its grain. The buttons' tongues are
    a bit thinner than the groove, so screwing them pulls the top down
    onto the aprons, and short of its bottom, so the top can move in and out.
    """
    asm = Assembly("table", root_location=STANDING)
    _, aprons = _table_frame(
        asm,
        width,
        depth,
        height - top_stock.thickness,
        apron_width,
        setback,
        leg_stock,
        stock,
        shoulder=(10, 30),
        haunch_length=10,
    )
    top = asm.add(Board("top", top_stock, length=width + 2 * overhang, width=depth + 2 * overhang))
    # The top lies on the aprons (their back edges are up), overhanging the legs.
    apron_front = aprons[0]
    asm.join(
        Butt(
            apron_front.back_edge,
            top.bottom_face,
            position=offset(-(leg_stock.thickness + overhang), ref=apron_front.left_end),
            flush=(apron_front.ref_face, top.front_edge),
            across=offset(-(setback + overhang)),
        )
    )

    # The buttons' groove is 8 mm wide and 6 deep, 12 below the top of the apron.
    groove_top, groove_width, groove_depth = 12.0, 8.0, 6.0
    button_width, gap = 40.0, 2.0  # gap: between the button and the apron, and in the groove
    tongue_length = groove_depth  # across the gap, and short of the groove's bottom by as much
    for apron in aprons:
        apron.cut(
            Groove(
                apron.bottom_face,
                width=groove_width,
                depth=groove_depth,
                distance=groove_top,
                ref=apron.back_edge,
            )
        )
    # A button is as thick as the groove's bottom is below the top; its tongue
    # at the bottom of its right end, `gap` thinner than the groove.
    button_stock = Stock.board(thickness=groove_top + groove_width, species=stock.species)
    inside = overhang + setback + stock.thickness + gap  # from the top's edge to a button
    for apron, top_edge, along, count in [
        (aprons[0], top.front_edge, top.left_end, buttons[0]),
        (aprons[1], top.right_end, top.front_edge, buttons[1]),
        (aprons[2], top.back_edge, top.right_end, buttons[0]),
        (aprons[3], top.left_end, top.back_edge, buttons[1]),
    ]:
        span = apron.length
        for i in range(count):
            name = f"button_{apron.name.removeprefix('apron_')}_{i + 1}"
            button = asm.add(Board(name, button_stock, length=30, width=button_width))
            button.cut(
                Tongue(
                    button.right_end,
                    length=tongue_length,
                    thickness=groove_width - gap,
                    thickness_offset=groove_top + gap,
                )
            )
            # Spread along the apron, between the legs.
            distance = overhang + leg_stock.thickness + span * (i + 0.5) / count
            asm.join(
                Butt(
                    top.bottom_face,
                    button.top_face,
                    position=offset(distance - button_width / 2, ref=along),
                    flush=(top_edge, button.right_end),
                    across=offset(inside),
                )
            )
    return asm
