"""Small practical projects: shop tools, boxes, shelves, drawers, frames, tables, a chair,
stools, a coat rack and a workbench."""

import itertools
import math

from woodwright import rules
from woodwright.assembly import Assembly
from woodwright.cuts import INF, Chamfer, EndChamfer, Hole, Mitre, Pocket, Taper
from woodwright.examples._common import BOX_FRONT, CASE_SIDE, OAK, SIDE_OAK, STANDING, THIN_OAK
from woodwright.examples.frames import _frame
from woodwright.joints import (
    Bore,
    Bridle,
    Butt,
    Button,
    DadoJoint,
    DovetailHalfLap,
    Dowels,
    DowelTuskTenon,
    HalfBlindDovetail,
    HalfLap,
    Joint,
    MitreCorner,
    MitredShoulderTenon,
    MortiseTenon,
    RabbetJoint,
    RoundMortiseTenon,
    Screw,
    SlidingDovetail,
    ThroughDovetail,
    TongueAndGroove,
    WedgedRoundMortiseTenon,
)
from woodwright.part import Board, Rod, SideRef
from woodwright.placement import (
    BACK,
    CENTERED,
    FRONT,
    LEFT,
    UP,
    Position,
    flush_with,
    offset,
    orient,
)
from woodwright.stock import Stock

SQUARE_STOCK = Stock.board(thickness=24, species="oak")
BEECH = Stock.board(thickness=60, species="beech")
ASH = Stock.board(thickness=24, species="ash")
THICK_OAK = Stock.board(thickness=30, species="oak")
DOOR_OAK = Stock.board(thickness=22, species="oak")  # for the frame of a door
PANEL_OAK = Stock.board(thickness=14, species="oak")  # for raised panels
CABINET_DOOR_OAK = Stock.board(thickness=20, species="oak")  # for a small door's frame
PLYWOOD = Stock.board(thickness=6, species="plywood")
GLASS = Stock.board(thickness=6, species="glass")

LEG_STOCK = Stock.board(thickness=45, species="oak")
BOW_SAW_STOCK = Stock.board(thickness=22, species="oak")
TABLE_LEG_STOCK = Stock.board(thickness=60, species="oak")
CHAIR_LEG_STOCK = Stock.board(thickness=40, species="oak")
ROUND_LEG_STOCK = Stock.rod(diameter=40, species="oak")
STRETCHER_STOCK = Stock.rod(diameter=25, species="oak")
PEG_STOCK = Stock.rod(diameter=22, species="oak")
BENCH_LEG_STOCK = Stock.board(thickness=90, species="oak")  # glued up from two 45 mm boards
BENCH_STOCK = Stock.board(thickness=45, species="oak")  # rails, stretchers, top beams
BENCH_DOWEL_STOCK = Stock.rod(diameter=20, species="oak")
TRAY_DOWEL_STOCK = Stock.rod(diameter=10, species="oak")
TUSK_STOCK = Stock.rod(diameter=25, species="oak")


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
    through tenons (see `stepstool`), which cross their grain.
    """
    asm = Assembly("stepstool_seat")
    _stepstool_seat(asm, length, depth, boards, batten_width, batten_inset, slope, stock)
    return asm


def _stepstool_seat(
    asm: Assembly,
    length: float,
    depth: float,
    boards: int,
    batten_width: float,
    batten_inset: float,
    slope: float,
    stock: Stock,
) -> tuple[list[Board], list[Board]]:
    """The seat boards and the battens of `stepstool_seat`."""
    seat = [
        asm.add(Board(f"seat_{i + 1}", stock, length=length, width=depth / boards))
        for i in range(boards)
    ]
    for a, b in itertools.pairwise(seat):
        asm.join(Butt(a.back_edge, b.front_edge))
    battens = []
    for name in ("left", "right"):
        batten = asm.add(Board(f"batten_{name}", stock, length=depth, width=batten_width))
        battens.append(batten)
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
    return seat, battens


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
    and `ledge_inset` in from the sides, are screwed to each board from
    the back, one screw in the middle of each board, so that the boards can
    still move; no braces.
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
        for i, board in enumerate(door):
            at = {ledge.left_end: (i + 0.5) * board.width - ledge_inset}
            asm.join(Screw(ledge.top_face, into=board, length=30, at=at))
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


def cabinet_door(
    height: float = 600,
    width: float = 400,
    member_width: float = 30,
    mitre_depth: float = 10,
    groove_width: float = 6,
    groove_depth: float = 8,
    clearance: float = 2,
    stock: Stock = CABINET_DOOR_OAK,
    bottom_panel_stock: Stock = PLYWOOD,
    top_panel_stock: Stock = GLASS,
) -> Assembly:
    """A small cabinet door of 2 x 3 cm stock with mitred shoulder tenons,
    a plywood panel below the middle rail and a glass one above; outside sizes.

    Two stiles, a top, a middle and a bottom rail. A groove runs through
    along the inside edges of all of them, centered in the thickness, the
    panels as thick as it is wide. Each rail reaches `mitre_depth` into a
    notch in the stile, mitred at 45 degrees at its inside edges, where the
    grooves meet like in a mitred frame; the notch is deeper than the
    grooves, so they don't show at the ends of the stiles. The tenons are as
    thick as the grooves are wide and keep out of them, reaching only a
    little under the mitres. At the corners, mitred only inside, they go
    through the stiles, with full shoulders towards the ends; the middle
    rail, mitred at both edges, has a hidden stub tenon.

    The panels don't move with moisture, but are set `clearance` short of
    the bottoms of the grooves all round, e.g. for glazing putty at the glass.
    The frame has to be glued up round them.
    """
    rail_length = width - 2 * member_width

    def corner(rail_end: SideRef, stile_edge: SideRef, position: Position, outer: SideRef) -> Joint:
        rail = rail_end.part
        inner = rail.back_edge if outer == rail.front_edge else rail.front_edge
        shoulders = (mitre_depth, groove_depth)
        return MitredShoulderTenon(
            tenon=rail_end,
            mortise=stile_edge,
            position=position,
            mitre_depth=mitre_depth,
            mitred=(inner,),
            shoulder=shoulders if outer == rail.front_edge else shoulders[::-1],
            tenon_thickness=groove_width,
            tenon_length=member_width - mitre_depth,  # through
        )

    asm, (stile_left, stile_right, rail_top, rail_bottom) = _frame(
        "cabinet_door", corner, height, rail_length, member_width, stock
    )
    # The rails' front edges are at the top.
    rail_middle = asm.add(Board("rail_middle", stock, length=rail_length, width=member_width))
    for rail_end, stile_edge, stile_end in [
        (rail_middle.left_end, stile_left.back_edge, stile_left.left_end),
        (rail_middle.right_end, stile_right.front_edge, stile_right.left_end),
    ]:
        asm.join(
            MitredShoulderTenon(
                tenon=rail_end,
                mortise=stile_edge,
                position=offset((height - member_width) / 2, stile_end),
                mitre_depth=mitre_depth,
                shoulder=groove_depth,
                tenon_thickness=groove_width,
                tenon_length=13,  # leaving 5 mm behind the mortise
            )
        )

    opening_height = (height - 3 * member_width) / 2
    reach = groove_depth - clearance
    # Lying like the rails, the front edges up.
    for name, panel_stock, above, below, stile_end in [
        ("top", top_panel_stock, rail_top, rail_middle, "right_end"),
        ("bottom", bottom_panel_stock, rail_middle, rail_bottom, "left_end"),
    ]:
        if panel_stock.thickness != groove_width:
            raise ValueError(f"the {name} panel must be as thick as the groove is wide")
        panel = asm.add(Board(f"panel_{name}", panel_stock, rail_length, opening_height))
        for side, groove, position in [
            (panel.left_end, stile_left.back_edge, getattr(stile_left, stile_end)),
            (panel.right_end, stile_right.front_edge, getattr(stile_right, stile_end)),
            (panel.front_edge, above.back_edge, None),
            (panel.back_edge, below.front_edge, None),
        ]:
            asm.join(
                TongueAndGroove(
                    tongue=side,
                    groove=groove,
                    tongue_thickness=groove_width,
                    tongue_length=reach,
                    cut_tongue=False,
                    position=CENTERED if position is None else offset(member_width, position),
                    across=CENTERED,
                    clearance=clearance,
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
    asm: Assembly,
    aprons: list[Board],
    buttons: tuple[int, int],
    stock: Stock,
    top: list[Board],
    overhang: float,
) -> list[Board]:
    """Buttons holding the top down, in short mortises in the inside of the aprons.

    `buttons` along the front and back, and along the sides, spread between
    the legs. The top moves across its grain: in and out of the mortises at
    the front and back, along them at the sides, where they are longer.
    Each button is screwed to the board of the `top` (from `_glued_top`,
    overhanging the frame by `overhang` at the front) above it.
    """
    button_width = 40.0
    # The legs' width, and the frame's depth outside them.
    leg_width = (top[0].length - 2 * overhang - aprons[0].length) / 2
    depth = aprons[1].length + 2 * leg_width
    top_thickness = top[0].thickness
    screw_length = stock.thickness + 5 * round(top_thickness / 10)
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
            # The button's center from the front of the top: the side aprons
            # run from the front (right) and from the back (left).
            along = leg_width + distance + button_width / 2
            from_front = [0.0, along, depth, depth - along][i] + overhang
            board = top[min(int(from_front // top[0].width), len(top) - 1)]
            asm.join(Screw(button.bottom_face, into=board, length=screw_length))
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
    top = _glued_top(
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
    _buttons(asm, aprons, buttons, stock, top, overhang)
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
    top = _glued_top(
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
    _buttons(asm, aprons, buttons, stock, top, overhang)
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


def _wedged_legs(
    asm: Assembly,
    seat: list[Board],
    leg_length: float,
    inset: tuple[float, float],
    tenon: float,
    kerf: float,
    flare: float,
    wedge_length: float,
    gap: float = 0.0,
    stock: Stock = ROUND_LEG_STOCK,
) -> list[Rod]:
    """Four round legs with tenons `tenon` wide through the front and the back
    boards of a `seat`, wedged; their axes `inset` in from the ends and from
    the front and back edges. With `gap`, their shoulders stand that far
    below the seat, e.g. under battens they pass through.

    The legs (front left, front right, back right, back left) stand with
    their left ends on the floor, their front edges to the front. Each
    wedge is `wedge_length` long, and as thick as fits within the tenon;
    its kerf runs across the seat's grain.
    """
    r = stock.diameter / 2
    width = kerf + 2 * flare
    thickness = math.floor(2 * math.sqrt((tenon / 2) ** 2 - (width / 2) ** 2))
    wedge_stock = Stock.board(thickness=thickness, species=stock.species)
    front, back = seat[0], seat[-1]
    corners = [
        ("front_left", front, "left_end", "front_edge"),
        ("front_right", front, "right_end", "front_edge"),
        ("back_right", back, "right_end", "back_edge"),
        ("back_left", back, "left_end", "back_edge"),
    ]
    legs = []
    for name, board, end, edge in corners:
        leg = asm.add(Rod(f"leg_{name}", stock, length=leg_length))
        legs.append(leg)
        wedge = asm.add(Board(f"wedge_{name}", wedge_stock, length=wedge_length, width=width))
        asm.join(
            WedgedRoundMortiseTenon(
                tenon=leg.right_end,
                mortise=board.bottom_face,
                diameter=tenon,
                position=offset(inset[0] - r, ref=getattr(board, end)),
                flush=(getattr(board, edge), getattr(leg, edge)),
                across=offset(inset[1] - r),
                gap=gap,
                wedge=wedge,
                kerf=kerf,
            )
        )
        leg.cut(EndChamfer(leg.left_end, size=2))
    return legs


def _rod_stretchers(
    asm: Assembly,
    legs: list[Rod],
    spans: list[tuple[str, int, float]],
    between: tuple[float, float],
    tenon: float,
    stock: Stock = STRETCHER_STOCK,
) -> None:
    """Round stretchers between adjacent round legs from `_wedged_legs`, with
    round tenons `tenon` wide, 25 mm into cross holes in the legs.

    Each span is a name, the leg it starts at (going round: front left,
    front right, back right, back left) and the height of its axis above
    the floor. `between` are the distances between the legs' axes, from
    side to side and from front to back. Stretchers at one leg go at
    different heights, so that their holes don't meet inside it.
    """
    # Facing the next leg round: to the right, to the back, to the left, to the front.
    out = ["bottom_face", "back_edge", "top_face", "front_edge"]
    into = ["top_face", "front_edge", "bottom_face", "back_edge"]
    for name, i, height in spans:
        # From the shoulder at one leg to the shoulder at the next.
        length = between[i % 2] - legs[i].diameter
        stretcher = asm.add(Rod(name, stock, length=length))
        for end, leg, side in [
            (stretcher.left_end, legs[i], out[i]),
            (stretcher.right_end, legs[(i + 1) % 4], into[i]),
        ]:
            asm.join(
                RoundMortiseTenon(
                    tenon=end,
                    mortise=getattr(leg, side),
                    diameter=tenon,
                    length=25,
                    position=offset(height - stock.diameter / 2, ref=leg.left_end),
                )
            )


def stool(
    width: float = 360,
    depth: float = 300,
    height: float = 450,
    seat_boards: int = 2,
    leg_inset: float = 55,
    tenon: float = 25,
    stretcher_heights: tuple[float, float] = (150, 190),
    seat_chamfer: float = 3,
    stock: Stock = THICK_OAK,
) -> Assembly:
    """A stool: four round legs wedged through a solid seat, round stretchers
    between them; straight legs (splayed ones come later).

    The seat, glued up from `seat_boards` boards edge to edge, its grain
    from side to side, is `height` above the floor; its arrises are
    chamfered all round on top. The legs' axes are `leg_inset` in from the
    seat's ends and edges; their round tenons, `tenon` wide, go through the
    seat flush with its top, each wedged in a kerf across the seat's grain,
    so that the wedge spreads the tenon along the grain and doesn't split
    the seat. The stretchers (their axes at `stretcher_heights`, for the
    front and back and for the sides) have round tenons in cross holes in
    the legs, the side ones higher, so that the holes don't meet.
    """
    floor = orient(at=(0, 0, height - stock.thickness), top_face=UP, back_edge=BACK)
    asm = Assembly("stool", root_location=floor)
    seat = [
        asm.add(Board(f"seat_{i + 1}", stock, length=width, width=depth / seat_boards))
        for i in range(seat_boards)
    ]
    for a, b in itertools.pairwise(seat):
        asm.join(Butt(a.back_edge, b.front_edge))
    for board in seat:
        sides = [board.left_end, board.right_end]
        sides += [
            edge
            for edge, outer in [(board.front_edge, seat[0]), (board.back_edge, seat[-1])]
            if board is outer
        ]
        for side in sides:
            board.cut(Chamfer(board.arris(board.top_face, side), size=seat_chamfer))
    legs = _wedged_legs(
        asm,
        seat,
        height - stock.thickness,
        (leg_inset, leg_inset),
        tenon,
        kerf=2,
        flare=2,
        wedge_length=20,
    )
    front_back, sides = stretcher_heights
    spans = [
        ("stretcher_front", 0, front_back),
        ("stretcher_right", 1, sides),
        ("stretcher_back", 2, front_back),
        ("stretcher_left", 3, sides),
    ]
    between = (width - 2 * leg_inset, depth - 2 * leg_inset)
    _rod_stretchers(asm, legs, spans, between, tenon=16)
    return asm


def stepstool(
    height: float = 250,
    length: float = 400,
    depth: float = 280,
    batten_width: float = 90,
    batten_inset: float = 30,
    leg_inset: float = 50,
    tenon: float = 25,
    stretcher_height: float = 90,
    stock: Stock = OAK,
) -> Assembly:
    """A step stool: the seat of `stepstool_seat` on four round legs, which go
    through the battens and the seat, wedged; straight legs (splayed ones
    come later).

    The legs stand under the middle of the battens, their axes `leg_inset`
    in from the front and the back. Their shoulders bear on the battens;
    the tenons, `tenon` wide, go through a hole bored through each batten
    and on through the seat, flush with its top, wedged across the seat's
    grain. The tenons cross the battens' grain, so that the battens hold the
    seat's boards. A round stretcher under each batten, its axis
    `stretcher_height` above the floor, joins the front and the back leg.
    """
    floor = orient(at=(0, 0, height - stock.thickness), top_face=UP, back_edge=BACK)
    asm = Assembly("stepstool", root_location=floor)
    seat, battens = _stepstool_seat(
        asm, length, depth, 2, batten_width, batten_inset, slope=4, stock=stock
    )
    batten = battens[0].thickness
    x = batten_inset + batten_width / 2
    legs = _wedged_legs(
        asm,
        seat,
        height - stock.thickness - batten,
        (x, leg_inset),
        tenon,
        kerf=2,
        flare=1.5,
        wedge_length=15,
        gap=batten,
    )
    # The front left and the back left leg go through the left batten.
    for leg, batten_part in zip(
        legs, [battens[0], battens[1], battens[1], battens[0]], strict=True
    ):
        asm.join(Bore(batten_part, leg.right_end, diameter=tenon))
    spans = [("stretcher_right", 1, stretcher_height), ("stretcher_left", 3, stretcher_height)]
    _rod_stretchers(asm, legs, spans, (length - 2 * x, depth - 2 * leg_inset), tenon=16)
    return asm


def coat_rack(
    length: float = 600,
    width: float = 100,
    pegs: int = 5,
    peg_length: float = 80,
    tenon: float = 12,
    chamfer: float = 3,
    stock: Stock = OAK,
) -> Assembly:
    """A coat rack: a board on the wall with `pegs` round pegs, evenly spaced.

    The pegs (`peg_length` long from the board) have round tenons `tenon`
    wide, glued into blind holes in the board's front, their ends
    chamfered. The board's front arrises along its length are chamfered;
    it is screwed to the wall through two counterbored holes between the
    outer pegs, to be closed by plugs.
    """
    asm = Assembly("coat_rack", root_location=orient(top_face=FRONT, back_edge=UP))
    board = asm.add(Board("board", stock, length=length, width=width))
    for edge in (board.front_edge, board.back_edge):
        board.cut(Chamfer(board.arris(board.top_face, edge), size=chamfer))
    pitch = length / pegs
    for i in range(pegs):
        peg = asm.add(Rod(f"peg_{i + 1}", PEG_STOCK, length=peg_length))
        peg.cut(EndChamfer(peg.right_end, size=2))
        asm.join(
            RoundMortiseTenon(
                tenon=peg.left_end,
                mortise=board.top_face,
                diameter=tenon,
                length=15,
                chamfer=1,
                position=offset((i + 0.5) * pitch - PEG_STOCK.diameter / 2, ref=board.left_end),
            )
        )
    for end in (board.left_end, board.right_end):
        board.cut(
            Hole(
                board.top_face,
                5,
                at={end: pitch},
                counterbore=10,
                counterbore_depth=8,
                kind="screw hole",
                note="for a 4.5 x 50 screw into the wall",
            )
        )
    return asm


def workbench(
    length: float = 2000,
    depth: float = 600,
    height: float = 900,
    overhang: float = 400,
    stretcher_width: float = 300,
    stretcher_height: float | None = None,
    lower_rail_height: float = 120,
    leg_cap: float = 30,
    tusks: int = 2,
    top_beams: int = 7,
    tray_thickness: float = 20,
) -> Assembly:
    """A knock-down workbench, an approximation of Rex Krueger's Quick Stack
    workbench (get his plans for the real thing, at rexkrueger.com).

    Two leg assemblies, `length` - 2 x `overhang` apart over the outsides of
    the legs, are joined by two wide stretchers with tusk tenons, and carry
    a split top `height` above the floor: a massive desk at the front and a
    tray (a drawer-like box) at the back, flush with the legs at the front
    and the back, `depth` deep, `overhang` beyond the legs at each end.

    Each leg assembly: two 90 mm square legs, their feet chamfered, and two
    rails from front to back, all glued up from two 45 mm boards (the legs'
    glue lines on their sides, the rails' upright), the rails flush
    with the legs' front and back, lapped across the legs but let in only
    partly: the rails are cut to half their thickness, the legs notched a
    quarter of theirs, so the rails stand out of the legs by a quarter. The
    lower rail, as square as the legs, is on the outside, `lower_rail_height`
    above the floor. The upper one, 90 x 135 mm, on the inside and flush
    with the tops of the legs, has its laps cut to half dovetails, flat at
    the bottom and sloped at the top: the laps are cut back `leg_cap` from
    the top, so that the legs keep a solid cap above the notches.

    The stretchers, 45 mm thick and `stretcher_width` wide, stand on the
    lower rails (or `stretcher_height` above the floor). Their long through
    tenons, as thick as the stretchers and a third as wide, stand out of the
    legs by as much as the legs are wide, their corners chamfered big. Each
    tenon is held by `tusks` dowel tusks (in the second and the fourth fifth
    of the tenon), level through its thickness, their heads to the front:
    20 mm dowels a bit longer than the legs are wide, their flats tapering
    over 50 mm at their tips, bearing on a half dowel glued flat side down
    on the leg behind the tenon.

    The desk is glued up from `top_beams` 45 x 90 mm beams standing on edge
    (as "2x4s"). The tray, of `tray_thickness` boards, has walls as high as
    the desk is thick and a bottom between them, flush with their lower
    edges, so that it can be turned over: open side up it holds tools,
    upside down it is a flat part of the top. Both sit on the legs and the
    upper rails, located by short dowels in the rails: two 20 mm ones into
    the desk (into two of its beams) and a 10 mm one into the tray's front
    wall on each rail; the back wall has matching holes in its top edge for
    the tray turned over.
    """
    leg_size, beam = BENCH_LEG_STOCK.thickness, BENCH_STOCK.thickness
    beam_height = 2 * beam
    leg_length = height - beam_height
    span = length - 2 * overhang  # over the outsides of the legs
    if stretcher_height is None:
        stretcher_height = lower_rail_height + leg_size
    root = orient(at=(overhang, 0, 0), right_end=UP, top_face=LEFT)
    asm = Assembly("workbench", root_location=root)

    # The leg assemblies; the right one is the mirror image of the left one.
    legs: dict[str, dict[str, Board]] = {}
    upper_rails: dict[str, Board] = {}
    lap = dict(lap_thickness=leg_size / 2, over=True, proud=leg_size / 4)
    for side, mirror in [("left", False), ("right", True)]:
        front, back = (
            asm.add(
                Board(
                    f"{side}_{end}_leg",
                    BENCH_LEG_STOCK,
                    leg_length,
                    leg_size,
                    mirror=mirror,
                    plies=2,
                    plies_across="width",
                )
            )
            for end in ("front", "back")
        )
        legs[side] = {"front": front, "back": back}
        for leg in (front, back):
            leg.cut(EndChamfer(leg.left_end, size=5))
        between = depth - 2 * leg_size
        lower, upper = (
            asm.add(
                Board(
                    f"{side}_{level}_rail", BENCH_LEG_STOCK, between, width, mirror=mirror, plies=2
                )
            )
            for level, width in [("lower", leg_size), ("upper", 1.5 * leg_size)]
        )
        upper_rails[side] = upper
        for end, leg in [(lower.left_end, front), (lower.right_end, back)]:
            asm.join(
                HalfLap(
                    lap=end,
                    socket=leg.back_edge if leg is front else leg.front_edge,
                    position=offset(lower_rail_height, ref=leg.left_end),
                    flush=(leg.top_face, lower.top_face),
                    **lap,
                )
            )
        for end, leg in [(upper.left_end, front), (upper.right_end, back)]:
            asm.join(
                DovetailHalfLap(
                    lap=end,
                    socket=leg.back_edge if leg is front else leg.front_edge,
                    position=flush_with(leg.right_end),
                    flush=(leg.bottom_face, upper.top_face),
                    stopped={leg.right_end: leg_cap},
                    slope=6,
                    sloped=(upper.back_edge,),
                    **lap,
                )
            )

    # The stretchers, their reference faces outside, through the inner faces of the legs.
    tenon_width = stretcher_width / 3
    for end in ("front", "back"):
        stretcher = asm.add(
            Board(f"{end}_stretcher", BENCH_STOCK, span - 2 * leg_size, stretcher_width)
        )
        for side, tenon in [("left", stretcher.left_end), ("right", stretcher.right_end)]:
            leg = legs[side][end]
            name = f"{end}_{side}"
            tusk_rods = tuple(
                asm.add(Rod(f"{name}_tusk_{i + 1}", BENCH_DOWEL_STOCK, length=110))
                for i in range(tusks)
            )
            bearing = asm.add(Rod(f"{name}_bearing", BENCH_DOWEL_STOCK, length=tenon_width))
            asm.join(
                DowelTuskTenon(
                    tenon=tenon,
                    mortise=leg.bottom_face,
                    position=offset(stretcher_height, ref=leg.left_end),
                    flush=(
                        (leg.front_edge, stretcher.top_face)
                        if end == "front"
                        else (leg.back_edge, stretcher.top_face)
                    ),
                    across=CENTERED,
                    shoulder=(stretcher_width - tenon_width) / 2,
                    tenon_thickness=beam,
                    tenon_chamfer=3,
                    tenon_corner_chamfer=25,
                    tusks=tusk_rods,
                    bearings=(bearing,),
                    tusk_head=leg.front_edge,
                    tusk_slope=12.5,
                    flat_length=50,
                    protrusion=leg_size,
                )
            )

    # The desk: beams on edge, their reference faces to the front, glued face to face.
    beams = [
        asm.add(Board(f"top_beam_{i + 1}", BENCH_STOCK, length, beam_height))
        for i in range(top_beams)
    ]
    for a, b in itertools.pairwise(beams):
        asm.join(Butt(a.bottom_face, b.top_face))

    # The tray: the front and the back as long as the bench, the ends between
    # them, the bottom between all four, flush with their lower edges; the
    # reference faces outside.
    tray_stock = Stock.board(thickness=tray_thickness, species="oak")
    tray_front_y = top_beams * beam
    tray_depth = depth - tray_front_y
    inside = tray_depth - 2 * tray_thickness
    tray_front, tray_back = (
        asm.add(Board(f"tray_{end}", tray_stock, length, beam_height)) for end in ("front", "back")
    )
    tray_ends = []
    for end in ("left", "right"):
        wall = asm.add(Board(f"tray_{end}", tray_stock, inside, beam_height))
        tray_ends.append(wall)
        asm.join(
            Butt(
                tray_front.bottom_face,
                wall.left_end,
                position=flush_with(getattr(tray_front, f"{end}_end")),
                flush=(tray_front.front_edge, wall.front_edge),
            )
        )
    for wall, outer in zip(
        tray_ends, (tray_ends[0].bottom_face, tray_ends[1].top_face), strict=True
    ):
        asm.join(
            Butt(
                wall.right_end,
                tray_back.bottom_face,
                position=flush_with(outer),
                flush=(wall.front_edge, tray_back.front_edge),
            )
        )
    bottom = asm.add(Board("tray_bottom", tray_stock, length - 2 * tray_thickness, inside))
    asm.join(
        Butt(
            tray_front.bottom_face,
            bottom.front_edge,
            flush=(tray_front.front_edge, bottom.bottom_face),
        )
    )

    # Dowels into the tops of the upper rails, which start behind the front
    # legs (at y = leg_size), in line with the legs but for the quarter
    # standing out of them.
    for side in ("left", "right"):
        rail = upper_rails[side]
        inner = overhang + leg_size if side == "left" else length - overhang - leg_size
        x = inner - 3 * leg_size / 4 if side == "left" else inner - leg_size / 4
        # A thinner dowel into the tray's wall, a third of its thickness.
        for board, front_y, stock, dowel_length in [
            (beams[top_beams // 2], top_beams // 2 * beam, BENCH_DOWEL_STOCK, 50),
            (beams[-1], (top_beams - 1) * beam, BENCH_DOWEL_STOCK, 50),
            (tray_front, tray_front_y, TRAY_DOWEL_STOCK, 40),
        ]:
            dowel = asm.add(Rod(f"{board.name}_dowel_{side}", stock, length=dowel_length))
            asm.join(
                Dowels(
                    board.front_edge,
                    rail.back_edge,
                    dowels=(dowel,),
                    offsets=(front_y + board.thickness / 2 - leg_size,),
                    flush=(board.top_face, rail.left_end),
                    across=offset(leg_size - front_y),
                    position=offset(x, ref=board.left_end),
                )
            )
        # The tray's back wall comes over the rail when the tray is turned over.
        tray_back.cut(
            Hole(
                tray_back.back_edge,
                TRAY_DOWEL_STOCK.diameter,
                depth=21,
                at={tray_back.left_end: length - x - leg_size / 2},
                kind="dowel hole",
                note="for the tray turned over",
            )
        )
    return asm
