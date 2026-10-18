"""Small practical projects: shop tools, boxes, shelves, drawers, frames, tables and a chair."""

import itertools
import math

from woodwright import rules
from woodwright.assembly import Assembly
from woodwright.cuts import INF, Chamfer, Mitre, Pocket, Taper
from woodwright.examples._common import BOX_FRONT, CASE_SIDE, OAK, SIDE_OAK, STANDING, THIN_OAK
from woodwright.examples.frames import _frame
from woodwright.joints import (
    Bridle,
    Butt,
    Button,
    DadoJoint,
    HalfBlindDovetail,
    Joint,
    MitreCorner,
    MortiseTenon,
    RabbetJoint,
    SlidingDovetail,
    ThroughDovetail,
    TongueAndGroove,
)
from woodwright.part import Board, SideRef
from woodwright.placement import BACK, CENTERED, UP, Position, flush_with, offset, orient
from woodwright.stock import Stock

SQUARE_STOCK = Stock.board(thickness=24, species="oak")
BEECH = Stock.board(thickness=60, species="beech")
ASH = Stock.board(thickness=24, species="ash")
THICK_OAK = Stock.board(thickness=30, species="oak")
DOOR_OAK = Stock.board(thickness=22, species="oak")  # for the frame of a door
PANEL_OAK = Stock.board(thickness=14, species="oak")  # for raised panels

LEG_STOCK = Stock.board(thickness=45, species="oak")
BOW_SAW_STOCK = Stock.board(thickness=22, species="oak")
TABLE_LEG_STOCK = Stock.board(thickness=60, species="oak")
CHAIR_LEG_STOCK = Stock.board(thickness=40, species="oak")


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


def bench_hook(
    length: float = 250,
    width: float = 180,
    fence_length: float = 150,
    fence_width: float = 40,
    stock: Stock = OAK,
    fence_stock: Stock = THICK_OAK,
) -> Assembly:
    """A bench hook: a base with a fence on top at the back and a hook below
    at the front, glued face to face across the grain.

    The base's grain runs away from the woodworker. The fence stops short of
    the right side, so the saw cuts into the base, not the fence; the hook
    spans the whole width.
    """
    # The base lies flat, its length away from the viewer: its back edge is
    # to the left.
    asm = Assembly("bench_hook", root_location=orient(right_end=BACK, ref_face=UP))
    base = asm.add(Board("base", stock, length=length, width=width))
    fence = asm.add(Board("fence", fence_stock, length=fence_length, width=fence_width))
    hook = asm.add(Board("hook", fence_stock, length=width, width=fence_width))
    asm.join(
        Butt(
            base.top_face,
            fence.bottom_face,
            flush=(base.right_end, fence.back_edge),
            position=flush_with(base.back_edge),
        )
    )
    asm.join(Butt(base.bottom_face, hook.top_face, flush=(base.left_end, hook.front_edge)))
    return asm


def stepstool_seat(
    length: float = 400,
    depth: float = 280,
    boards: int = 2,
    batten_width: float = 90,
    batten_inset: float = 30,
    slope: float = 4,
    stock: Stock = OAK,
) -> Assembly:
    """The seat of a stepstool: boards edge to edge, two battens underneath
    across the grain, in wide, shallow sliding dovetail housings.

    The battens lie flat, `batten_inset` in from the ends, and keep the seat
    flat and its boards together, even without glue; not glued, they let it
    shrink and swell across its grain. Each batten's whole width goes into a
    housing a third of the seat deep, its edges bevelled by 1:`slope`, and
    runs across all the boards, housed in each of them. The housings run
    through, out of the front and the back edges, where the battens' ends
    are flush with the seat's. The battens are wide enough for the legs'
    through tenons (not modelled), which cross their grain.
    """
    asm = Assembly("stepstool_seat")
    seat = [
        asm.add(Board(f"seat_{i + 1}", stock, length=length, width=depth / boards))
        for i in range(boards)
    ]
    for a, b in itertools.pairwise(seat):
        asm.join(Butt(a.back_edge, b.front_edge))
    for name in ("left", "right"):
        batten = asm.add(Board(f"batten_{name}", stock, length=depth, width=batten_width))
        # The batten's top face runs from the front (its left end) to the
        # back, across each board in turn; the first joint cuts its tongue.
        for i, board in enumerate(seat):
            asm.join(
                SlidingDovetail(
                    socket=board.bottom_face,
                    end=batten.top_face,
                    slope=slope,
                    position=offset(batten_inset, ref=getattr(board, f"{name}_end")),
                    flush=(board.front_edge, batten.left_end),
                    across=offset(-i * depth / boards),
                    cut_tongue=i == 0,
                )
            )
    return asm


def ledged_door(
    height: float = 600,
    width: float = 400,
    boards: int = 4,
    ledge_width: float = 80,
    ledge_from_ends: float = 80,
    ledge_inset: float = 15,
    chamfer: float = 3,
    stock: Stock = OAK,
) -> Assembly:
    """A ledged cupboard door: tongue-and-groove boards on two ledges across the back.

    The boards stand side by side, each tongued into a groove along the
    next, not glued, so they can move; the outer boards' outer edges are
    plain. On the front the arrises along the joints are chamfered, so
    that each joint shows as a V and a gap opening as the boards shrink
    is hidden. The ledges, `ledge_from_ends` from the top and the bottom
    and `ledge_inset` in from the sides, would be screwed to each board
    from the back (the screws aren't modelled); no braces.
    """
    # The boards' reference faces are at the back, their back edges to the right.
    asm = Assembly("ledged_door", root_location=STANDING)
    door = [
        asm.add(Board(f"board_{i + 1}", stock, length=height, width=width / boards))
        for i in range(boards)
    ]
    for a, b in itertools.pairwise(door):
        asm.join(TongueAndGroove(tongue=b.front_edge, groove=a.back_edge))
        for edge in (a.back_edge, b.front_edge):
            edge.part.cut(Chamfer(edge.part.arris(edge.part.bottom_face, edge), size=chamfer))
    first = door[0]
    for name, end in [("top", first.right_end), ("bottom", first.left_end)]:
        ledge = asm.add(
            Board(f"ledge_{name}", stock, length=width - 2 * ledge_inset, width=ledge_width)
        )
        asm.join(
            Butt(
                first.top_face,
                ledge.bottom_face,
                position=offset(ledge_from_ends, ref=end),
                flush=(first.front_edge, ledge.left_end),
                across=offset(ledge_inset),
            )
        )
    return asm


def ledged_and_braced_door(
    height: float = 1000,
    width: float = 600,
    boards: int = 5,
    ledge_width: float = 100,
    ledge_from_ends: float = 100,
    ledge_inset: float = 20,
    brace_width: float = 100,
    brace_inset: float = 20,
    stock: Stock = OAK,
) -> Assembly:
    """A ledged and braced door, e.g. for a shed: boards butted edge to edge
    on two ledges and a diagonal brace across the back.

    The boards aren't glued: they would be nailed or screwed to the ledges
    and the brace from the front (not modelled). The ledges lie
    `ledge_from_ends` from the top and the bottom, `ledge_inset` in from
    the sides. The brace lies between them, in the same plane, and keeps
    the door from sagging: it rises from the hinge side (the left, seen
    from the front) at the bottom ledge to the latch side at the top one,
    so that it is in compression. Its ends are cut level and bear against
    the ledges' edges, the long points `brace_inset` in from the ends of
    the ledges.
    """
    # The boards' reference faces are at the back, their back edges to the right.
    asm = Assembly("ledged_and_braced_door", root_location=STANDING)
    door = [
        asm.add(Board(f"board_{i + 1}", stock, length=height, width=width / boards))
        for i in range(boards)
    ]
    for a, b in itertools.pairwise(door):
        asm.join(Butt(a.back_edge, b.front_edge))
    first = door[0]
    for name, end in [("top", first.right_end), ("bottom", first.left_end)]:
        ledge = asm.add(
            Board(f"ledge_{name}", stock, length=width - 2 * ledge_inset, width=ledge_width)
        )
        asm.join(
            Butt(
                first.top_face,
                ledge.bottom_face,
                position=offset(ledge_from_ends, ref=end),
                flush=(first.front_edge, ledge.left_end),
                across=offset(ledge_inset),
            )
        )
    # The brace's long points, on its upper (front) edge at the bottom and
    # its lower (back) edge at the top, lie on the ledges' edges, `run` apart
    # across the door and `rise` apart up it: its slope makes the brace's
    # width fit between them.
    rise = height - 2 * (ledge_from_ends + ledge_width)
    run = width - 2 * (ledge_inset + brace_inset)
    slope = math.atan2(rise, run) + math.asin(brace_width / math.hypot(run, rise))
    length = (rise + brace_width * math.cos(slope)) / math.sin(slope)
    brace = asm.add(Board("brace", stock, length=length, width=brace_width))
    end_angle = 90 - math.degrees(slope)
    brace.cut(Mitre(brace.left_end, inside=brace.back_edge, angle=end_angle))
    brace.cut(Mitre(brace.right_end, inside=brace.front_edge, angle=end_angle))
    # Lying along the top of the door, the brace is turned down about its
    # lower long point, on the bottom ledge (measured from the top).
    asm.join(
        Butt(
            first.top_face,
            brace.bottom_face,
            position=offset(height - ledge_from_ends - ledge_width),
            flush=(first.front_edge, brace.left_end),
            across=offset(ledge_inset + brace_inset),
            angle=-math.degrees(slope),
        )
    )
    return asm


def frame_and_panel_door(
    height: float = 800,
    width: float = 500,
    member_width: float = 65,
    groove_width: float = 8,
    groove_depth: float = 10,
    tenon_length: float = 40,
    muntin_tenon_length: float = 25,
    bevel: float = 30,
    clearance: float = 2,
    stock: Stock = DOOR_OAK,
    panel_stock: Stock = PANEL_OAK,
) -> Assembly:
    """A door of four raised panels in a mortise-and-tenon frame; outside sizes.

    Two stiles, a top, a middle and a bottom rail, and between the rails
    above and below the middle one a short muntin. A groove runs through
    along the inside edges of all of them, centered in the thickness, as
    cut on a table saw. The rails are tenoned into the stiles, the muntins
    into the rails, the tenons as thick as the grooves are wide and with
    shoulders as wide as they are deep, so that the grooves run out beside
    them. At the ends of the stiles, the tenons of the top and the bottom
    rails have haunches filling the grooves; the muntins' short tenons
    leave room for each other in the middle rail.

    The panels, the grain upright, are raised on the front, their backs
    flat: the bevel, as planed by hand, runs from the field right out to the
    edges, at the mouths of the grooves (`bevel` out from the field) as
    thick as the grooves are wide, and on into them, getting thinner; the
    field of a 14 mm panel lies 1 mm behind the face of a 22 mm frame. They
    aren't glued, but float in the grooves: the edges are `clearance` short
    of the bottom across the grain, so the panels can swell, and 1 mm along
    it.
    """
    rail_length = width - 2 * member_width

    def corner(rail_end: SideRef, stile_edge: SideRef, position: Position, outer: SideRef) -> Joint:
        return MortiseTenon(
            tenon=rail_end,
            mortise=stile_edge,
            position=position,
            tenon_length=tenon_length,
            haunch=outer,
            haunch_length=groove_depth,
            tenon_thickness=groove_width,
            shoulder=groove_depth,
        )

    asm, (stile_left, stile_right, rail_top, rail_bottom) = _frame(
        "frame_and_panel_door", corner, height, rail_length, member_width, stock
    )
    # The rails' front edges are at the top.
    rail_middle = asm.add(Board("rail_middle", stock, length=rail_length, width=member_width))
    middle = (height - member_width) / 2
    for rail_end, stile_edge, stile_end in [
        (rail_middle.left_end, stile_left.back_edge, stile_left.left_end),
        (rail_middle.right_end, stile_right.front_edge, stile_right.left_end),
    ]:
        asm.join(
            MortiseTenon(
                tenon=rail_end,
                mortise=stile_edge,
                position=offset(middle, stile_end),
                tenon_length=tenon_length,
                tenon_thickness=groove_width,
                shoulder=groove_depth,
            )
        )
    # Standing like the stiles: their right ends up, back edges to the right.
    opening_height = middle - member_width
    muntins = []
    for name, top, bottom in [
        ("top", rail_top, rail_middle),
        ("bottom", rail_middle, rail_bottom),
    ]:
        muntin = asm.add(Board(f"muntin_{name}", stock, length=opening_height, width=member_width))
        for end, rail_edge in [
            (muntin.right_end, top.back_edge),
            (muntin.left_end, bottom.front_edge),
        ]:
            asm.join(
                MortiseTenon(
                    tenon=end,
                    mortise=rail_edge,
                    tenon_length=muntin_tenon_length,
                    tenon_thickness=groove_width,
                    shoulder=groove_depth,
                )
            )
        muntins.append(muntin)

    def into_groove(edge: SideRef, groove: SideRef, position: Position, length: float) -> None:
        # The bevelled edge goes in whole, the back of the panel against the
        # back of the groove.
        asm.join(
            TongueAndGroove(
                tongue=edge,
                groove=groove,
                tongue_thickness=groove_width,
                tongue_length=length,
                tongue_offset=0,
                cut_tongue=False,
                position=position,
                across=offset((stock.thickness - groove_width) / 2),
                clearance=groove_depth - length,
            )
        )

    # Standing like the stiles too, their reference faces at the back: the
    # front edges to the left, the right ends up.
    opening_width = (rail_length - member_width) / 2
    edge_reach, end_reach = groove_depth - clearance, groove_depth - 1
    for row, muntin, above, under, stile_end in [
        ("top", muntins[0], rail_top.back_edge, rail_middle.front_edge, "right_end"),
        ("bottom", muntins[1], rail_middle.back_edge, rail_bottom.front_edge, "left_end"),
    ]:
        for column, stile_groove, muntin_groove, rail_end in [
            ("left", stile_left.back_edge, muntin.front_edge, "left_end"),
            ("right", stile_right.front_edge, muntin.back_edge, "right_end"),
        ]:
            panel = asm.add(
                Board(f"panel_{row}_{column}", panel_stock, opening_height, opening_width)
            )
            outer, inner = panel.front_edge, panel.back_edge
            if column == "right":
                outer, inner = inner, outer
            stile_position = offset(member_width, getattr(stile_groove.part, stile_end))
            into_groove(outer, stile_groove, stile_position, edge_reach)
            into_groove(inner, muntin_groove, CENTERED, edge_reach)
            for end, groove in [(panel.right_end, above), (panel.left_end, under)]:
                into_groove(end, groove, flush_with(getattr(groove.part, rail_end)), end_reach)
            # On the design box, the bevel ends at the mouth of the groove.
            for side in (panel.front_edge, panel.back_edge, panel.left_end, panel.right_end):
                panel.cut(
                    Chamfer(
                        panel.arris(panel.bottom_face, side),
                        size=bevel,
                        size_b=panel_stock.thickness - groove_width,
                        run_out=True,
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


def butt_shelf(
    height: float = 600,
    width: float = 500,
    depth: float = 200,
    stock: Stock = OAK,
) -> Assembly:
    """Two sides with a top, a bottom and a middle shelf butted between them,
    e.g. to be screwed through the sides (the screws aren't modelled).

    Outside sizes; the shelves' design length is between the sides.
    """
    t = stock.thickness
    asm = Assembly("butt_shelf", root_location=CASE_SIDE)
    left = asm.add(Board("left", stock, length=height, width=depth))
    right = asm.add(Board("right", stock, length=height, width=depth, mirror=True))
    top = asm.add(Board("top", stock, length=width - 2 * t, width=depth))
    bottom = asm.add(Board("bottom", stock, length=width - 2 * t, width=depth))
    shelf = asm.add(Board("shelf", stock, length=width - 2 * t, width=depth))
    for side, top_end, bottom_end, shelf_end in [
        (left, top.left_end, bottom.left_end, shelf.left_end),
        (right, top.right_end, bottom.right_end, shelf.right_end),
    ]:
        asm.join(Butt(side.bottom_face, top_end, position=flush_with(side.right_end)))
        asm.join(Butt(side.bottom_face, bottom_end, position=flush_with(side.left_end)))
        asm.join(Butt(side.bottom_face, shelf_end, position=offset(height / 2, side.right_end)))
    return asm


def dovetail_shelf(
    height: float = 500,
    width: float = 400,
    depth: float = 200,
    tail_count: int = 3,
    stock: Stock = OAK,
) -> Assembly:
    """A shelf of two stories: a case through-dovetailed at its four corners
    and a middle shelf in dados; outside sizes.

    The sides have pins at both ends, the top and the bottom tails, so the
    tails show on the sides. The sides' and the top's design lengths are
    shorter by the boards they reach through.
    """
    t = stock.thickness
    asm = Assembly("dovetail_shelf", root_location=CASE_SIDE)
    left = asm.add(Board("left", stock, length=height - 2 * t, width=depth))
    right = asm.add(Board("right", stock, length=height - 2 * t, width=depth, mirror=True))
    top = asm.add(Board("top", stock, length=width - 2 * t, width=depth))
    bottom = asm.add(Board("bottom", stock, length=width - 2 * t, width=depth, mirror=True))
    shelf = asm.add(Board("shelf", stock, length=width - 2 * t, width=depth))
    for side, top_end, bottom_end, shelf_end in [
        (left, top.left_end, bottom.left_end, shelf.left_end),
        (right, top.right_end, bottom.right_end, shelf.right_end),
    ]:
        asm.join(ThroughDovetail(tails=top_end, pins=side.right_end, tail_count=tail_count))
        asm.join(ThroughDovetail(tails=bottom_end, pins=side.left_end, tail_count=tail_count))
        asm.join(
            DadoJoint(
                dado=side.bottom_face,
                end=shelf_end,
                position=offset((height - 2 * t) / 2, side.right_end),
            )
        )
    return asm


def rabbeted_box(
    length: float = 300,
    depth: float = 200,
    height: float = 100,
    stock: Stock = SIDE_OAK,
    bottom_stock: Stock = THIN_OAK,
) -> Assembly:
    """An open box: the sides' ends in rabbets at the ends of the front and
    the back, the bottom in rabbets along the inside of the walls' bottom
    edges, flush with them; outside sizes.

    The sides and the bottom are as long (and wide) as the inside of the
    box; the rabbets add to them. The back and the right side are mirror
    images of the front and the left side, all with their reference faces
    outside.
    """
    t = stock.thickness
    asm = Assembly("rabbeted_box", root_location=BOX_FRONT)
    front = asm.add(Board("front", stock, length=length, width=height))
    back = asm.add(Board("back", stock, length=length, width=height, mirror=True))
    left = asm.add(Board("left", stock, length=depth - 2 * t, width=height))
    right = asm.add(Board("right", stock, length=depth - 2 * t, width=height, mirror=True))
    # The bottom lies with its reference face down; mirrored, so that its
    # left end is still at the left.
    bottom = asm.add(
        Board("bottom", bottom_stock, length=length - 2 * t, width=depth - 2 * t, mirror=True)
    )
    # The sides' right ends are at the front, so that their front edges are
    # at the bottom, as the other walls' are.
    for side, front_end, back_end in [
        (left, front.left_end, back.left_end),
        (right, front.right_end, back.right_end),
    ]:
        asm.join(RabbetJoint(rabbet=front.bottom_face, end=side.right_end, at=front_end))
        asm.join(RabbetJoint(rabbet=back.bottom_face, end=side.left_end, at=back_end))
    for wall, edge in [
        (front, bottom.front_edge),
        (back, bottom.back_edge),
        (left, bottom.left_end),
        (right, bottom.right_end),
    ]:
        # Along the front and the back, the rabbet runs into those at the corners.
        through = wall in (front, back)
        asm.join(
            RabbetJoint(rabbet=wall.bottom_face, end=edge, at=wall.front_edge, through=through)
        )
    return asm


def bow_saw_frame(
    arm_length: float = 350,
    arm_width: float = 40,
    stretcher_length: float = 500,
    stretcher_width: float = 30,
    stock: Stock = BOW_SAW_STOCK,
) -> Assembly:
    """The frame of a bow saw: two arms and a stretcher between their middles,
    tenoned into their inner edges.

    The blade (at the bottom) and the string (at the top) aren't modelled.
    """
    asm = Assembly("bow_saw_frame", root_location=STANDING)
    left = asm.add(Board("left_arm", stock, length=arm_length, width=arm_width))
    right = asm.add(Board("right_arm", stock, length=arm_length, width=arm_width))
    stretcher = asm.add(Board("stretcher", stock, length=stretcher_length, width=stretcher_width))
    # The arms face each other with their back and front edges.
    for tenon, mortise in [
        (stretcher.left_end, left.back_edge),
        (stretcher.right_end, right.front_edge),
    ]:
        asm.join(MortiseTenon(tenon=tenon, mortise=mortise, tenon_length=25))
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
    leg_lengths: tuple[float, float, float, float] | None = None,
    apron_name: str = "apron",
) -> tuple[list[Board], list[Board]]:
    """Four legs and four aprons with mitred tenons; outside sizes.

    Each apron goes from the back edge of one leg to the top face of the
    next one, so the legs are all the same, turned by 90 degrees around the
    table. The aprons have their reference faces outside and their back
    edges up; with `haunch_length` the tenons get haunches at the top.
    The aprons are flush with the tops of the legs, `height` above the
    floor; legs given longer in `leg_lengths` (front left, front right,
    back right, back left) reach above them, e.g. into a chair's back.
    """
    leg_width = leg_stock.thickness
    tenon = rules.tenon_thickness(stock.thickness)
    tenon_length = leg_width - setback - (stock.thickness - tenon) / 2
    names = ["front_left", "front_right", "back_right", "back_left"]
    lengths = leg_lengths or (height,) * 4
    legs = [
        asm.add(Board(f"leg_{name}", leg_stock, length=length, width=leg_width))
        for name, length in zip(names, lengths, strict=True)
    ]
    aprons = [
        asm.add(
            Board(f"{apron_name}_{name}", stock, length=length - 2 * leg_width, width=apron_width)
        )
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
                    position=offset(leg.length - height, ref=leg.right_end),
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


def _glued_top(
    asm: Assembly,
    apron: Board,
    name: str,
    width: float,
    depth: float,
    overhang: float,
    back_overhang: float,
    boards: int,
    leg_stock: Stock,
    setback: float,
    stock: Stock,
) -> list[Board]:
    """A top (or a seat) glued up from `boards` boards edge to edge, from the
    front to the back, its grain from side to side.

    It lies on the aprons of a frame of outside size `width` x `depth`
    (`apron` is the front one, its back edge up), overhanging it by
    `overhang` at the front and the sides and by `back_overhang` at the back.
    """
    board_width = (depth + overhang + back_overhang) / boards
    top = [
        asm.add(Board(f"{name}_{i + 1}", stock, length=width + 2 * overhang, width=board_width))
        for i in range(boards)
    ]
    for a, b in itertools.pairwise(top):
        asm.join(Butt(a.back_edge, b.front_edge))
    asm.join(
        Butt(
            apron.back_edge,
            top[0].bottom_face,
            position=offset(-(leg_stock.thickness + overhang), ref=apron.left_end),
            flush=(apron.ref_face, top[0].front_edge),
            across=offset(-(setback + overhang)),
        )
    )
    return top


def _buttons(
    asm: Assembly, aprons: list[Board], buttons: tuple[int, int], stock: Stock
) -> list[Board]:
    """Buttons holding the top down, in short mortises in the inside of the aprons.

    `buttons` along the front and back, and along the sides, spread between
    the legs. The top moves across its grain: in and out of the mortises at
    the front and back, along them at the sides, where they are longer.
    """
    button_width = 40.0
    placed = []
    for i, apron in enumerate(aprons):
        count, play = (buttons[0], 1.0) if i % 2 == 0 else (buttons[1], 5.0)
        for j in range(count):
            name = f"button_{apron.name.removeprefix('apron_')}_{j + 1}"
            button = asm.add(Board(name, stock, length=30, width=button_width))
            placed.append(button)
            # Spread along the apron, between the legs.
            distance = apron.length * (j + 0.5) / count - button_width / 2
            asm.join(
                Button(
                    mortise=apron.bottom_face,
                    tongue=button.right_end,
                    level=apron.back_edge,
                    position=offset(distance, ref=apron.left_end),
                    play=play,
                )
            )
    return placed


Span = tuple[str, int, float, float]  # name, leg it starts at, level of its top edge, width


def _stretchers(heights: tuple[float, float], stretcher_width: float) -> list[Span]:
    """Stretchers all round, their top edges at `heights` (front and back, sides)."""
    front_back, sides = heights
    names = ["front", "right", "back", "left"]
    levels = [front_back, sides, front_back, sides]
    return [
        (f"stretcher_{name}", i, level, stretcher_width)
        for i, (name, level) in enumerate(zip(names, levels, strict=True))
    ]


def _leg_rails(
    asm: Assembly,
    legs: list[Board],
    width: float,
    depth: float,
    spans: list[Span],
    stock: Stock,
    mitred: bool = False,
    **tenon: float,
) -> dict[str, Board]:
    """Rails (e.g. stretchers) between adjacent legs of a frame from `_table_frame`.

    Like the aprons, each goes from the back edge of one leg (`legs[i]`) to
    the top face of the next one, but centered on them, its top edge at its
    level above the floor; `tenon` are options of its tenons (`MortiseTenon`).
    With `mitred`, rails at the same level have mitred tenons meeting on the
    leg's diagonal, like the aprons, each reaching to the far cheek of the other.
    """
    leg_width = legs[0].width
    if mitred:
        tenon.setdefault("tenon_length", (leg_width + rules.tenon_thickness(stock.thickness)) / 2)
    rails = {}
    for name, i, level, rail_width in spans:
        length = width if i % 2 == 0 else depth
        rail = rails[name] = asm.add(
            Board(name, stock, length=length - 2 * leg_width, width=rail_width)
        )
        this_leg, next_leg = legs[i], legs[(i + 1) % 4]
        for end, leg, mortise, outside in [
            (rail.left_end, this_leg, this_leg.back_edge, this_leg.bottom_face),
            (rail.right_end, next_leg, next_leg.top_face, next_leg.front_edge),
        ]:
            asm.join(
                MortiseTenon(
                    tenon=end,
                    mortise=mortise,
                    position=offset(leg.length - level, ref=leg.right_end),
                    flush=(outside, rail.ref_face),
                    across=CENTERED,
                    mitre=rail.bottom_face if mitred else None,
                    **tenon,
                )
            )
    return rails


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
    top_boards: int = 4,
    buttons: tuple[int, int] = (3, 2),
    leg_stock: Stock = TABLE_LEG_STOCK,
    stock: Stock = OAK,
    top_stock: Stock = THICK_OAK,
) -> Assembly:
    """A table: legs and wide aprons, a solid top held down by buttons; outside sizes.

    `width` and `depth` are those of the frame, the top overhangs it by
    `overhang`. The aprons are wide, so their tenons are set down from the
    top of the legs, with haunches filling the wide shoulders: the legs
    keep their tops whole, and the aprons can't twist. The top is glued up
    from `top_boards` boards edge to edge, its grain from side to side. It
    is not glued to the frame: wooden buttons screwed to its underside have
    tongues in short mortises in the inside of the aprons (`buttons` along
    the front and back, and along the sides), so it can move across its
    grain: in and out of the mortises at the front and back, along them at
    the sides, where they are longer.
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
    _glued_top(
        asm,
        aprons[0],
        "top",
        width,
        depth,
        overhang,
        overhang,
        top_boards,
        leg_stock,
        setback,
        top_stock,
    )
    _buttons(asm, aprons, buttons, stock)
    return asm


def side_table(
    width: float = 400,
    depth: float = 400,
    height: float = 550,
    overhang: float = 25,
    apron_width: float = 80,
    stretcher_width: float = 30,
    stretcher_height: float = 150,
    setback: float = 3,
    top_boards: int = 3,
    buttons: tuple[int, int] = (2, 2),
    leg_stock: Stock = CHAIR_LEG_STOCK,
    stock: Stock = OAK,
) -> Assembly:
    """A side table: legs, aprons and stretchers, a solid top held down by
    buttons; outside sizes.

    As in the table, the aprons' mitred tenons are set down from the tops
    of the legs, with haunches; the top, glued up from `top_boards` boards,
    overhangs the frame by `overhang` and is held by buttons in short
    mortises in the aprons, so it can move. Stretchers near the floor, all
    at the same level (their top edges at `stretcher_height`), are centered
    on the legs, with blind tenons mitred at their ends like the aprons',
    meeting inside the legs.
    """
    asm = Assembly("side_table", root_location=STANDING)
    legs, aprons = _table_frame(
        asm,
        width,
        depth,
        height - stock.thickness,
        apron_width,
        setback,
        leg_stock,
        stock,
        shoulder=(10, 20),
        haunch_length=10,
    )
    stretchers = _stretchers((stretcher_height, stretcher_height), stretcher_width)
    _leg_rails(asm, legs, width, depth, stretchers, stock, mitred=True)
    _glued_top(
        asm,
        aprons[0],
        "top",
        width,
        depth,
        overhang,
        overhang,
        top_boards,
        leg_stock,
        setback,
        stock,
    )
    _buttons(asm, aprons, buttons, stock)
    return asm


def chair(
    width: float = 440,
    depth: float = 420,
    seat_height: float = 450,
    height: float = 900,
    rail_width: float = 80,
    stretcher_width: float = 30,
    stretcher_heights: tuple[float, float] = (230, 180),
    back_rails: tuple[float, float] = (620, 870),
    back_rail_width: float = 60,
    setback: float = 3,
    protrusion: float = 2,
    tenon_chamfer: float = 2,
    top_chamfer: float = 4,
    overhang: float = 10,
    seat_boards: int = 2,
    seat_chamfer: float = 3,
    splats: int = 3,
    splat_width: float = 30,
    splat_tenon_length: float = 20,
    leg_taper: float = 5,
    leg_taper_length: float = 140,
    leg_stock: Stock = CHAIR_LEG_STOCK,
    stock: Stock = OAK,
    seat_stock: Stock = OAK,
) -> Assembly:
    """A simple chair, all square; outside sizes of the frame.

    The back legs run up into the back. Under the seat, rails `rail_width`
    wide are tenoned into the legs as in a table frame, flush with the tops
    of the front legs. The seat, a panel glued up from `seat_boards` boards
    edge to edge, its grain from side to side, lies on them, its top
    `seat_height` above the floor; it overhangs the frame by `overhang` at
    the front and the sides and the back board is notched at the corners
    around the back legs, flush with their outsides. The arrises around
    the seat, top and bottom, are chamfered. Stretchers near the floor and
    two rails in the back (their top edges at `stretcher_heights`, for the
    front and back and for the sides, and at `back_rails`) have through
    tenons standing `protrusion` proud of the legs, their ends chamfered.
    The side stretchers are lower than the front and back ones, so that the
    tenons don't meet inside the legs. Between the back rails stand
    `splats`, as thick as the rails, with blind tenons in their edges. The
    tops of the back legs are chamfered all round; the legs taper on their
    inner sides from `leg_taper_length` above the floor, below the
    stretchers, to `leg_taper` thinner at the floor.
    """
    asm = Assembly("chair", root_location=STANDING)
    seat = seat_height - seat_stock.thickness
    legs, rails = _table_frame(
        asm,
        width,
        depth,
        seat,
        rail_width,
        setback,
        leg_stock,
        stock,
        leg_lengths=(seat, seat, height, height),
        apron_name="seat_rail",
    )
    back_rail_spans = [
        (f"back_rail_{name}", 2, level, back_rail_width)
        for name, level in zip(["lower", "upper"], back_rails, strict=True)
    ]
    members = _leg_rails(
        asm,
        legs,
        width,
        depth,
        _stretchers(stretcher_heights, stretcher_width) + back_rail_spans,
        stock,
        tenon_length=leg_stock.thickness + protrusion,
        tenon_chamfer=tenon_chamfer,
    )
    for leg in legs[2:]:
        for side in (leg.top_face, leg.bottom_face, leg.front_edge, leg.back_edge):
            leg.cut(Chamfer(leg.arris(leg.right_end, side), size=top_chamfer))
    # The outer sides of the legs are their bottom faces and front edges.
    for leg in legs:
        for side in (leg.top_face, leg.back_edge):
            leg.cut(Taper(side, end=leg.left_end, amount=leg_taper, length=leg_taper_length))

    # The splats stand evenly spaced between the back rails, whose back edges are up.
    lower, upper = members["back_rail_lower"], members["back_rail_upper"]
    splat_length = back_rails[1] - back_rail_width - back_rails[0]
    gap = (lower.length - splats * splat_width) / (splats + 1)
    for j in range(splats):
        splat = asm.add(Board(f"splat_{j + 1}", stock, length=splat_length, width=splat_width))
        distance = gap + j * (gap + splat_width)
        for end, mortise in [
            (splat.left_end, lower.back_edge),
            (splat.right_end, upper.front_edge),
        ]:
            rail = mortise.part
            asm.join(
                MortiseTenon(
                    tenon=end,
                    mortise=mortise,
                    position=offset(distance, ref=rail.left_end),
                    flush=(rail.ref_face, splat.ref_face),
                    tenon_length=splat_tenon_length,
                )
            )

    boards = _glued_top(
        asm,
        rails[0],
        "seat",
        width,
        depth,
        overhang,
        0,
        seat_boards,
        leg_stock,
        setback,
        seat_stock,
    )
    front, back = boards[0], boards[-1]
    # The notches reach from the back edge (y = back.width) and the ends.
    leg_width = leg_stock.thickness
    notch_x, notch_y = overhang + leg_width, (back.width - leg_width, INF)
    for x in [(-INF, notch_x), (back.length - notch_x, INF)]:
        back.cut(Pocket(back.back_edge, (x, notch_y, (-INF, INF)), kind="notch"))
    for board in boards:
        sides = [board.left_end, board.right_end]
        sides += [
            edge
            for edge, outer in [(board.front_edge, front), (board.back_edge, back)]
            if board is outer
        ]
        for side in sides:
            for face in (board.top_face, board.bottom_face):
                board.cut(Chamfer(board.arris(face, side), size=seat_chamfer))
    return asm
