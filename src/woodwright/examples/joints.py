"""Joints of two parts: boards, rods, and the pieces joining them (wedges, dowels, pegs)."""

import itertools

from woodwright import rules
from woodwright.assembly import Assembly
from woodwright.cuts import Groove
from woodwright.examples._common import BOX_FRONT, CASE_SIDE, OAK, SIDE_OAK, STANDING, THIN_OAK
from woodwright.joints import (
    BlindMitredDovetail,
    BoxJoint,
    Bridle,
    Butt,
    CrossLap,
    DadoJoint,
    DovetailHalfLap,
    Dowels,
    GrooveJoint,
    HalfBlindDovetail,
    HalfLap,
    LooseTenon,
    LooseTongue,
    MitreCorner,
    MitredCornerDovetail,
    MitredFaceTenon,
    MitredHalfLap,
    MitredShoulderTenon,
    MitreSplice,
    MortiseTenon,
    PeggedMortiseTenon,
    RabbetJoint,
    RoundMortiseTenon,
    Screw,
    SlidingDovetail,
    TeeBridle,
    ThroughDovetail,
    TongueAndGroove,
    TuskTenon,
    WedgedMortiseTenon,
    WedgedRoundMortiseTenon,
)
from woodwright.part import Board, Rod
from woodwright.placement import CENTERED, FRONT, LEFT, UP, flush_with, offset, orient
from woodwright.stock import Stock

THICK_OAK = Stock.board(thickness=30, species="oak")  # also 30 x 45 mm (2:3) frame stock
LEG_STOCK = Stock.board(thickness=45, species="oak")
POST_STOCK = Stock.board(thickness=70, species="oak")
HOLLOW_LEG_OAK = Stock.board(thickness=15, species="oak")
SPLINE_OAK = Stock.board(thickness=6, species="oak")  # for loose tongues
ROD_OAK = Stock.rod(diameter=25, species="oak")  # rungs, stretchers
ROUND_LEG_OAK = Stock.rod(diameter=40, species="oak")
DOWEL_OAK = Stock.rod(diameter=8, species="oak")  # dowels and pegs


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
    asm = Assembly("butt_corner", root_location=CASE_SIDE)
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
    asm = Assembly("dado_shelf", root_location=CASE_SIDE)
    side = asm.add(Board("side", stock, length=side_height, width=depth))
    shelf = asm.add(Board("shelf", stock, length=shelf_length, width=depth))
    asm.join(
        DadoJoint(
            dado=side.bottom_face, end=shelf.left_end, position=offset(shelf_height, side.right_end)
        )
    )
    return asm


def stopped_dado_shelf(
    side_height: float = 400,
    shelf_length: float = 300,
    depth: float = 200,
    shelf_height: float = 150,
    stop: float = 15,
    stock: Stock = OAK,
) -> Assembly:
    """A shelf in a stopped dado, as in a bookshelf: the dado stops `stop`
    short of the side's front edge, so it doesn't show at the front.

    The shelf's front corner is notched to the stop, its front edge flush
    with the side's; at the back the dado runs out (under a back panel).
    """
    asm = Assembly("stopped_dado_shelf", root_location=CASE_SIDE)
    side = asm.add(Board("side", stock, length=side_height, width=depth))
    shelf = asm.add(Board("shelf", stock, length=shelf_length, width=depth))
    asm.join(
        DadoJoint(
            dado=side.bottom_face,
            end=shelf.left_end,
            position=offset(shelf_height, side.right_end),
            stopped={side.front_edge: stop},
        )
    )
    return asm


def rabbet_corner(
    side_height: float = 400, top_length: float = 500, depth: float = 200, stock: Stock = OAK
) -> Assembly:
    """A carcase corner: the end of the top in a rabbet at the top end of the side.

    The top's length is between the sides, the side's height is overall.
    """
    asm = Assembly("rabbet_corner", root_location=CASE_SIDE)
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
    asm = Assembly("sliding_dovetail_shelf", root_location=CASE_SIDE)
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
    asm = Assembly("interlocking_rabbet_corner", root_location=CASE_SIDE)
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


def loose_tongue_panel(
    length: float = 500,
    width: float = 150,
    count: int = 3,
    tongue_width: float = 20,
    stop: float = 20,
    stock: Stock = OAK,
) -> Assembly:
    """Boards glued edge to edge, a loose tongue in a groove along each of
    the two edges at every joint.

    The tongues are strips of 6 mm oak, their grain along the joint,
    `tongue_width` wide, half of it in each board. They stop `stop` short
    of the ends of the boards, in stopped grooves (cut with a router, here
    square-ended) 1 mm deeper than the tongues reach, so the ends of the
    panel show no grooves.
    """
    asm = Assembly("loose_tongue_panel")
    boards = [
        asm.add(Board(f"board_{i + 1}", stock, length=length, width=width)) for i in range(count)
    ]
    for i, (a, b) in enumerate(itertools.pairwise(boards)):
        tongue = asm.add(
            Board(f"tongue_{i + 1}", SPLINE_OAK, length=length - 2 * stop, width=tongue_width)
        )
        asm.join(LooseTongue(a.back_edge, b.front_edge, tongue, through=False))
    return asm


def shiplap_panel(
    length: float = 500, width: float = 150, lap: float = 12, count: int = 3, stock: Stock = OAK
) -> Assembly:
    """Boards edge to edge, lapped over each other in rabbets half their thickness.

    Along each joint the next board's rabbet, cut from below, lies over the
    previous one's, cut from above, `lap` wide: a "tongue" as thick as
    half the board, flush with its top face. Not glued, the boards can move
    and the lap covers the gap; the top shows a plain line at each joint.
    """
    asm = Assembly("shiplap_panel")
    boards = [
        asm.add(Board(f"board_{i + 1}", stock, length=length, width=width)) for i in range(count)
    ]
    for a, b in itertools.pairwise(boards):
        asm.join(
            TongueAndGroove(
                tongue=b.front_edge,
                groove=a.back_edge,
                tongue_thickness=rules.lap_thickness(stock.thickness),
                tongue_length=lap,
                tongue_offset=0,
            )
        )
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


def dovetail_half_lap(
    stile_length: float = 300, rail_length: float = 200, width: float = 40, stock: Stock = OAK
) -> Assembly:
    """A T-shaped dovetailed half lap: the lap on the rail cut to a tail, wider at
    its end than at the shoulder, in a socket of its shape across the stile.

    Unlike a plain half lap it holds even if the rail is pulled along its
    length, e.g. a cross rail pulled by a sagging top. The tail shows on the
    face towards the viewer.
    """
    asm = Assembly("dovetail_half_lap", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    asm.join(DovetailHalfLap(lap=rail.left_end, socket=stile.back_edge))
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


def bridle_t(
    stile_length: float = 400,
    rail_length: float = 300,
    width: float = 50,
    stock: Stock = OAK,
) -> Assembly:
    """A T-shaped bridle: a slot in the end of the rail straddles the stile,
    which is cut down to a tongue by a dado across each face.

    The rail's length is overall, to the far edge of the stile.
    """
    asm = Assembly("bridle_t", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    asm.join(TeeBridle(slot=rail.left_end, edge=stile.back_edge))
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


def _corner_tenon(
    name: str,
    stile_length: float,
    rail_length: float,
    width: float,
    tenon_length: float,
    outer_shoulder: float,
    inner_shoulder: float,
    haunch_length: float | None,
    stock: Stock,
) -> Assembly:
    """An L-shaped frame corner: the rail tenoned into the back edge of the
    stile, its front (outer) edge flush with the stile's right end, the tenon
    blind, optionally haunched towards the outer edge."""
    asm = Assembly(name, root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    asm.join(
        MortiseTenon(
            tenon=rail.left_end,
            mortise=stile.back_edge,
            position=flush_with(stile.right_end),
            tenon_length=tenon_length,
            shoulder=(outer_shoulder, inner_shoulder),  # the front edge is outer
            haunch=rail.front_edge if haunch_length else None,
            haunch_length=haunch_length,
        )
    )
    return asm


def stub_tenon_corner(
    stile_length: float = 300,
    rail_length: float = 200,
    width: float = 60,
    tenon_length: float = 40,
    outer_shoulder: float = 15,
    stock: Stock = OAK,
) -> Assembly:
    """A frame corner with a stub tenon: shoulders on the faces and the outer edge only.

    On the inner edge the tenon is flush with the rail, with no shoulder;
    on the outer edge a plain shoulder sets the mortise back from the end
    of the stile, so it stays closed there. No haunch. Blind, two thirds of
    the stile wide. Compare `haunched_stub_tenon_corner` and
    `haunched_mortise_tenon_corner`, same stock and tenon length.
    """
    return _corner_tenon(
        "stub_tenon_corner",
        stile_length,
        rail_length,
        width,
        tenon_length,
        outer_shoulder=outer_shoulder,
        inner_shoulder=0,
        haunch_length=None,
        stock=stock,
    )


def haunched_mortise_tenon_corner(
    stile_length: float = 300,
    rail_length: float = 200,
    width: float = 60,
    tenon_length: float = 40,
    outer_shoulder: float = 15,
    inner_shoulder: float = 10,
    haunch_length: float = 10,
    stock: Stock = OAK,
) -> Assembly:
    """A frame corner with a haunched tenon: shoulders on both edges, a haunch on the outer one.

    On the inner edge the tenon has a small shoulder, which hides the
    mortise; on the outer edge the shoulder sets the mortise back from the
    end of the stile, and a haunch, a short, shallow continuation of the
    tenon, fills it in a haunch mortise running out of the stile's end, so
    the rail can't twist. Unlike `haunched_stub_tenon_corner` (no inner
    shoulder) and `stub_tenon_corner` (no haunch either).
    """
    return _corner_tenon(
        "haunched_mortise_tenon_corner",
        stile_length,
        rail_length,
        width,
        tenon_length,
        outer_shoulder=outer_shoulder,
        inner_shoulder=inner_shoulder,
        haunch_length=haunch_length,
        stock=stock,
    )


def haunched_stub_tenon_corner(
    stile_length: float = 300,
    rail_length: float = 200,
    width: float = 60,
    tenon_length: float = 40,
    outer_shoulder: float = 15,
    haunch_length: float = 10,
    stock: Stock = OAK,
) -> Assembly:
    """A frame corner with a haunched stub tenon: a haunch on the outer edge, no inner shoulder.

    As `stub_tenon_corner`, the tenon is flush with the rail's inner edge;
    as `haunched_mortise_tenon_corner`, the outer shoulder is filled by a
    haunch in a haunch mortise running out of the end of the stile.
    """
    return _corner_tenon(
        "haunched_stub_tenon_corner",
        stile_length,
        rail_length,
        width,
        tenon_length,
        outer_shoulder=outer_shoulder,
        inner_shoulder=0,
        haunch_length=haunch_length,
        stock=stock,
    )


def twin_tenon_corner(
    stile_length: float = 500,
    rail_length: float = 300,
    stile_width: float = 70,
    rail_width: float = 150,
    outer_shoulder: float = 20,
    stock: Stock = OAK,
) -> Assembly:
    """A wide rail at a frame corner (e.g. the bottom rail of a door) with twin tenons.

    A single tenon as wide as the rail would need a long mortise weakening
    the stile, and would shrink and swell too much across its width; two
    tenons side by side, each in its own mortise, keep the material between
    them. The outer shoulder keeps the mortises away from the end of the stile.
    """
    asm = Assembly("twin_tenon_corner", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=stile_width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=rail_width))
    asm.join(
        MortiseTenon(
            tenon=rail.left_end,
            mortise=stile.back_edge,
            position=flush_with(stile.right_end),
            shoulder=(outer_shoulder, 10),  # the front edge is outer, at the end of the stile
            tenons=2,
            tenon_length=45,
        )
    )
    return asm


def _post_and_thick_rail(
    name: str,
    tenons: int,
    thickness_tenons: int,
    shoulder: float,
    tenon_thickness: float | None = None,
    gap: float | None = None,
) -> Assembly:
    """A 45 x 45 mm rail tenoned into a 70 x 70 mm post, centered on it;
    `gap` between the tenons both ways."""
    asm = Assembly(name, root_location=STANDING)
    post = asm.add(Board("post", POST_STOCK, length=500, width=POST_STOCK.thickness))
    rail = asm.add(Board("rail", LEG_STOCK, length=300, width=LEG_STOCK.thickness))
    asm.join(
        MortiseTenon(
            tenon=rail.left_end,
            mortise=post.back_edge,
            shoulder=shoulder,
            tenons=tenons,
            tenon_gap=gap,
            thickness_tenons=thickness_tenons,
            thickness_gap=gap,
            tenon_thickness=tenon_thickness,
            tenon_length=45,
            across=CENTERED,
        )
    )
    return asm


def thick_rail_tenons() -> Assembly:
    """A thick, square rail (e.g. a bench stretcher) tenoned into a post with
    two tenons one beside the other across its thickness.

    A single tenon a third of the rail thick would be weak in a square
    rail, a thicker one would leave thin mortise walls; two thinner tenons,
    each in its own mortise, give twice the glue area and keep the wood
    between them. Each is as thick as the gap between them and the
    shoulders, about a fifth of the rail; the shoulders at the edges are as
    deep as those at the cheeks.
    """
    return _post_and_thick_rail("thick_rail_tenons", tenons=1, thickness_tenons=2, shoulder=7.5)


def square_rail_four_tenons() -> Assembly:
    """A square rail tenoned into a post with four tenons in a 2 x 2 grid:
    two across the width as well as two across the thickness, each in its
    own mortise. The tenons are square, 12 mm, 8 mm apart both ways, with
    shoulders all round."""
    return _post_and_thick_rail(
        "square_rail_four_tenons",
        tenons=2,
        thickness_tenons=2,
        shoulder=6.5,
        tenon_thickness=12,
        gap=8,
    )


def _leg_and_aprons(
    name: str, tenon_length: float | None, mitred: bool, setback: float
) -> Assembly:
    """A table leg with two aprons tenoned into its two inner sides, tops flush."""
    asm = Assembly(name, root_location=STANDING)
    leg = asm.add(Board("leg", LEG_STOCK, length=700, width=LEG_STOCK.thickness))
    front = asm.add(Board("front_apron", OAK, length=400, width=100))
    side = asm.add(Board("side_apron", OAK, length=300, width=100))
    # The leg's outside sides are its bottom face and front edge; each apron's
    # reference face is outside, `setback` behind the leg's.
    for apron, mortise, outside in [
        (front, leg.back_edge, leg.bottom_face),
        (side, leg.top_face, leg.front_edge),
    ]:
        asm.join(
            MortiseTenon(
                tenon=apron.left_end,
                mortise=mortise,
                position=flush_with(leg.right_end),
                flush=(outside, apron.ref_face),
                across=offset(setback),
                tenon_length=tenon_length,
                shoulder=10,
                mitre=apron.bottom_face if mitred else None,
            )
        )
    return asm


def leg_and_aprons(tenon_length: float = 25, setback: float = 3) -> Assembly:
    """A table leg with two aprons, their short tenons not meeting inside the leg.

    The tenons must stay short: with the default length (two thirds of the
    leg) they would clash.
    """
    return _leg_and_aprons("leg_and_aprons", tenon_length, mitred=False, setback=setback)


def leg_and_aprons_mitred(setback: float = 3) -> Assembly:
    """A table leg with two aprons, their long tenons mitred to meet inside the leg.

    The tenons are as long as they can be: their long points (on the outer
    cheeks) lie on the diagonal of the leg.
    """
    tenon = rules.tenon_thickness(OAK.thickness)
    outer_cheek = setback + (OAK.thickness - tenon) / 2  # from the outside of the leg
    return _leg_and_aprons(
        "leg_and_aprons_mitred", LEG_STOCK.thickness - outer_cheek, mitred=True, setback=setback
    )


def loose_tenon(
    stile_length: float = 600,
    rail_length: float = 300,
    width: float = 60,
    tenon_length: float = 50,
    tenon_width: float = 40,
    stock: Stock = OAK,
) -> Assembly:
    """A rail joined to the back edge of a stile by a loose tenon.

    The loose tenon is a strip of 8 mm oak glued into a mortise in the
    stile's edge and one in the rail's end, half its length in each, as cut
    with a router or a domino jointer (the mortises here square-ended).
    """
    asm = Assembly("loose_tenon", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    tenon_stock = Stock.board(thickness=rules.tenon_thickness(stock.thickness), species="oak")
    tenon = asm.add(Board("loose_tenon", tenon_stock, length=tenon_length, width=tenon_width))
    asm.join(LooseTenon(stile.back_edge, rail.left_end, tenon))
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


def protruding_through_mortise_tenon(
    stile_length: float = 600,
    rail_length: float = 300,
    width: float = 60,
    protrusion: float = 10,
    stock: Stock = OAK,
) -> Assembly:
    """A through tenon standing `protrusion` proud of the stile, its end square."""
    asm = Assembly("protruding_through_mortise_tenon", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    asm.join(
        MortiseTenon(tenon=rail.left_end, mortise=stile.back_edge, tenon_length=width + protrusion)
    )
    return asm


def chamfered_through_mortise_tenon(
    stile_length: float = 600,
    rail_length: float = 300,
    width: float = 60,
    chamfer: float = 2,
    stock: Stock = OAK,
) -> Assembly:
    """A through tenon whose chamfered end alone stands proud of the stile,
    like a low pyramid on the stile's edge.

    The tenon is longer than the stile is wide by the chamfer, so the
    chamfers start where it leaves the stile.
    """
    asm = Assembly("chamfered_through_mortise_tenon", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    asm.join(
        MortiseTenon(
            tenon=rail.left_end,
            mortise=stile.back_edge,
            tenon_length=width + chamfer,
            tenon_chamfer=chamfer,
        )
    )
    return asm


def wedged_through_tenon(
    stile_length: float = 600,
    rail_length: float = 300,
    width: float = 60,
    kerf: float = 2,
    flare: float = 3,
    stock: Stock = OAK,
) -> Assembly:
    """A through tenon spread by two wedges into a mortise flared towards the outside.

    Two saw kerfs in the end of the tenon, near its edges, take the wedges;
    driven in, they bend the outer parts of the tenon out into the flares at
    the ends of the mortise, so the joint can't pull out even without glue.
    The mortise is flared along the stile, not across it, which would split
    it. The wedges are planed flush with the tenon; the stile stands with
    the tenon's end towards the viewer.
    """
    asm = Assembly("wedged_through_tenon", root_location=orient(right_end=UP, back_edge=LEFT))
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    # As thick as the tenon, as long as the kerfs (two thirds of the stile),
    # at the head as wide as the kerf and the spread.
    wedge_stock = Stock.board(thickness=rules.tenon_thickness(stock.thickness), species="oak")
    wedges = tuple(
        asm.add(Board(f"wedge_{i + 1}", wedge_stock, length=width * 2 / 3, width=kerf + flare))
        for i in range(2)
    )
    asm.join(
        WedgedMortiseTenon(
            tenon=rail.left_end, mortise=stile.back_edge, shoulder=10, wedges=wedges, kerf=kerf
        )
    )
    return asm


def _tusk_tenon(
    name: str,
    leg_length: float,
    stretcher_length: float,
    width: float,
    protrusion: float,
    tenon_thickness: float,
    wedge_head: str,
    wedge_size: tuple[float, float, float],
    wedge_slope: float,
) -> Assembly:
    """A stretcher through a standing leg, 100 mm below its top, held by a
    wedge through its tenon; `wedge_size` is its length, width and thickness.
    The leg stands with its reference face towards the viewer, the tenon
    sticking out of it to the right."""
    asm = Assembly(name, root_location=orient(right_end=UP, back_edge=LEFT))
    leg = asm.add(Board("leg", POST_STOCK, length=leg_length, width=POST_STOCK.thickness))
    stretcher = asm.add(Board("stretcher", LEG_STOCK, length=stretcher_length, width=width))
    length, wedge_width, thickness = wedge_size
    wedge_stock = Stock.board(thickness=thickness, species="oak")
    wedge = asm.add(Board("wedge", wedge_stock, length=length, width=wedge_width))
    asm.join(
        TuskTenon(
            tenon=stretcher.left_end,
            mortise=leg.back_edge,
            position=offset(100, ref=leg.right_end),
            across=CENTERED,
            shoulder=15,
            tenon_thickness=tenon_thickness,
            tenon_chamfer=2,
            wedge=wedge,
            wedge_head=getattr(leg, wedge_head),
            wedge_slope=wedge_slope,
            protrusion=protrusion,
        )
    )
    return asm


def tusk_tenon(
    leg_length: float = 500,
    stretcher_length: float = 400,
    width: float = 120,
    protrusion: float = 60,
) -> Assembly:
    """A tusk tenon with the wedge parallel to the stile: a knock-down joint
    of a workbench stretcher through a leg, the wedge upright.

    A 45 x 120 mm stretcher goes through a 70 mm square leg with a 90 x 25
    mm tenon (15 mm shoulders at the edges, 10 at the faces), its end
    chamfered, standing 60 mm proud. A 10 mm thick wedge, 150 mm long and
    25 wide at its head, tapered 1:10 at its back edge, is driven down
    through a mortise from the top edge of the tenon to its bottom edge,
    bearing on the outer face of the leg and pulling the shoulders tight;
    knocked up, it frees the stretcher.
    """
    return _tusk_tenon(
        "tusk_tenon",
        leg_length,
        stretcher_length,
        width,
        protrusion,
        tenon_thickness=25,
        wedge_head="right_end",
        wedge_size=(150, 25, 10),
        wedge_slope=10,
    )


def tusk_tenon_flat(
    leg_length: float = 500,
    stretcher_length: float = 400,
    width: float = 120,
    protrusion: float = 60,
) -> Assembly:
    """A tusk tenon with the wedge perpendicular to the stile: the wedge lies
    level, through the tenon's thickness, its head towards the viewer.

    As `tusk_tenon`, but the tenon is a usual third of the stretcher thick
    (16 mm), and the wedge, 20 mm thick, 80 long and 25 wide at its head,
    tapered 1:8, goes through a mortise from one cheek of the tenon to the
    other, in the middle of its width.
    """
    return _tusk_tenon(
        "tusk_tenon_flat",
        leg_length,
        stretcher_length,
        width,
        protrusion,
        tenon_thickness=16,
        wedge_head="top_face",
        wedge_size=(80, 25, 20),
        wedge_slope=8,
    )


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


def mitred_shoulder_tenon(
    stile_length: float = 600,
    rail_length: float = 300,
    width: float = 45,
    stock: Stock = THICK_OAK,
) -> Assembly:
    """A T-joint of square-ish stock: the rail reaches into a notch in the
    stile, mitred at both edges, and a stub tenon goes on from there.

    The rail meets the stile on two short 45-degree mitres (by default a
    third of the stile wide) with a straight line between them. The tenon
    reaches half-way under the mitres both ways, for strength; there the
    mitres are cut only down to its cheeks.
    """
    asm = Assembly("mitred_shoulder_tenon", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    asm.join(MitredShoulderTenon(tenon=rail.left_end, mortise=stile.back_edge))
    return asm


def mitred_shoulder_corner(
    stile_length: float = 300,
    rail_length: float = 200,
    width: float = 45,
    stock: Stock = THICK_OAK,
) -> Assembly:
    """An L-shaped frame corner of square-ish stock, mitred only at the inner edge.

    Like a mitre corner whose mitre stops a third into the stile; the rest
    is butted, with a through tenon behind the notch. The tenon reaches
    half-way under the mitre, but keeps a full shoulder towards the end of
    the stile, so that enough material is left there.
    """
    asm = Assembly("mitred_shoulder_corner", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    depth = width / 3
    asm.join(
        MitredShoulderTenon(
            tenon=rail.left_end,
            mortise=stile.back_edge,
            position=flush_with(stile.right_end),
            mitre_depth=depth,
            mitred=(rail.back_edge,),  # the inner edge
            tenon_length=width - depth,  # through
        )
    )
    return asm


# --- Box joints -------------------------------------------------------------


def box_joint_corner(
    front_length: float = 300,
    side_length: float = 200,
    height: float = 100,
    stock: Stock = SIDE_OAK,
) -> Assembly:
    """The corner of a box with a box (finger) joint: square fingers on both ends.

    The fingers come out close to the stock's thickness, nine of them, the
    front's at the top and the bottom edges. The lengths are outside
    dimensions: the boards reach through each other.
    """
    asm = Assembly("box_joint_corner", root_location=BOX_FRONT)
    t = stock.thickness
    front = asm.add(Board("front", stock, length=front_length - t, width=height))
    side = asm.add(Board("side", stock, length=side_length - t, width=height))
    asm.join(BoxJoint(front.left_end, side.right_end))
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
    asm = Assembly("dovetail_corner", root_location=CASE_SIDE)
    side = asm.add(Board("side", stock, length=side_height - stock.thickness, width=depth))
    top = asm.add(Board("top", stock, length=top_length - stock.thickness, width=depth))
    asm.join(ThroughDovetail(tails=top.left_end, pins=side.right_end, tail_count=tail_count))
    return asm


def half_blind_dovetail_corner(
    front_length: float = 400,
    side_length: float = 300,
    height: float = 150,
    tail_count: int = 3,
    stock: Stock = OAK,
    side_stock: Stock = SIDE_OAK,
) -> Assembly:
    """The front corner of a drawer: half-blind dovetails, the tails hidden behind a lap.

    The front's length is overall, the side's from the inside of the front.
    """
    asm = Assembly("half_blind_dovetail_corner", root_location=BOX_FRONT)
    t = side_stock.thickness
    front = asm.add(Board("front", stock, length=front_length - t, width=height))
    side = asm.add(Board("side", side_stock, length=side_length, width=height))
    asm.join(HalfBlindDovetail(tails=side.right_end, pins=front.left_end, tail_count=tail_count))
    return asm


def mitred_dovetail_corner(
    front_length: float = 400,
    side_length: float = 300,
    height: float = 150,
    groove_width: float = 6,
    groove_depth: float = 8,
    stock: Stock = OAK,
) -> Assembly:
    """The corner of a box made to be sawn open: through dovetails mitred at both edges.

    The top and the bottom panel go into grooves along the inside of the
    walls, `groove_width` from the edges; the mitres at the edges hide where
    the grooves run out of the ends. Outside lengths, as `dovetail_corner`.
    """
    asm = Assembly("mitred_dovetail_corner", root_location=BOX_FRONT)
    t = stock.thickness
    front = asm.add(Board("front", stock, length=front_length - t, width=height))
    side = asm.add(Board("side", stock, length=side_length - t, width=height))
    asm.join(
        MitredCornerDovetail(
            tails=side.right_end, pins=front.left_end, tail_count=3, mitre_width=2.5 * groove_width
        )
    )
    # Along the inside faces, through the ends, within the mitres.
    for board in (front, side):
        for edge in (board.front_edge, board.back_edge):
            board.cut(Groove(board.bottom_face, groove_width, groove_depth, groove_width, edge))
    return asm


def blind_mitred_dovetail_corner(
    side_height: float = 400,
    top_length: float = 500,
    depth: float = 200,
    tail_count: int = 4,
    stock: Stock = OAK,
) -> Assembly:
    """A carcase corner with blind mitred (secret mitre) dovetails: tails on the
    top, pins on the side, hidden behind mitred lips; outside dimensions.

    From outside, on the faces and on the edges, the corner looks like a mitre.
    """
    asm = Assembly("blind_mitred_dovetail_corner", root_location=CASE_SIDE)
    side = asm.add(Board("side", stock, length=side_height - stock.thickness, width=depth))
    top = asm.add(Board("top", stock, length=top_length - stock.thickness, width=depth))
    asm.join(BlindMitredDovetail(tails=top.left_end, pins=side.right_end, tail_count=tail_count))
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


def mitred_half_lap(
    stile_length: float = 300, rail_length: float = 200, width: float = 40, stock: Stock = OAK
) -> Assembly:
    """A frame corner mitred on the face and half-lapped behind: lengths to the outside.

    The front half of both parts is mitred, so the face towards the viewer
    looks like a mitre corner; at the back the stile keeps a lap across the
    whole corner, under the rail cut back by an end rabbet.
    """
    asm = Assembly("mitred_half_lap", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    asm.join(
        MitredHalfLap(
            stile.right_end, rail.left_end, stile.back_edge, rail.back_edge, face=stile.bottom_face
        )
    )
    return asm


def mitred_face_tenon_corner(
    stile_length: float = 300, rail_length: float = 200, width: float = 45, stock: Stock = THICK_OAK
) -> Assembly:
    """A frame corner mitred on the face, with a hidden mortise and tenon behind.

    The front third of both parts is mitred, so the face towards the viewer
    looks like a mitre corner, e.g. on a frame with a chamfered or moulded
    front. Behind it the stile runs on to the corner and the rail butts
    against its inside edge, with a 22.5 x 8 mm tenon, 30 mm long, centered
    in the layer behind the mitre and across the rail's width, in a blind
    mortise; it shows neither at the end of the stile nor at its outer edge.
    """
    asm = Assembly("mitred_face_tenon_corner", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    asm.join(
        MitredFaceTenon(
            stile.right_end, rail.left_end, stile.back_edge, rail.back_edge, face=stile.bottom_face
        )
    )
    return asm


def edge_mitre_corner(
    side_height: float = 400, top_length: float = 500, depth: float = 200, stock: Stock = OAK
) -> Assembly:
    """A carcase corner mitred across the edges, so no end grain shows; outside lengths."""
    asm = Assembly("edge_mitre_corner", root_location=CASE_SIDE)
    side = asm.add(Board("side", stock, length=side_height, width=depth))
    top = asm.add(Board("top", stock, length=top_length, width=depth))
    asm.join(MitreCorner(side.right_end, top.left_end, side.bottom_face, top.bottom_face))
    return asm


def hollow_leg(length: float = 700, width: float = 60, stock: Stock = HOLLOW_LEG_OAK) -> Assembly:
    """A square hollow leg: four boards glued along their edges, each edge
    mitred at 45 degrees along the grain, so they meet on the diagonals of
    the corners and no edge grain shows; outside sizes.

    Lighter than a solid leg and showing face grain on all four sides, with
    a square hole through its length (here 30 mm for 15 mm boards). The
    reference faces are outside; the boards stand with their left ends at
    the bottom.
    """
    asm = Assembly("hollow_leg", root_location=orient(right_end=UP, ref_face=FRONT))
    names = ("front", "left", "back", "right")
    boards = [asm.add(Board(name, stock, length=length, width=width)) for name in names]
    # Going round, each board's back edge meets the next one's front edge.
    for a, b in zip(boards, boards[1:] + boards[:1], strict=True):
        asm.join(MitreCorner(a.back_edge, b.front_edge, a.bottom_face, b.bottom_face))
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


# --- Round joints -----------------------------------------------------------


def rod_in_hole(leg_length: float = 450, rod_length: float = 300) -> Assembly:
    """A rod (a rung, a stretcher) going with its whole cross-section into a
    blind hole in a square leg, two thirds of the leg deep."""
    asm = Assembly("rod_in_hole", root_location=STANDING)
    leg = asm.add(Board("leg", LEG_STOCK, length=leg_length, width=45))
    rod = asm.add(Rod("rod", ROD_OAK, length=rod_length))
    asm.join(RoundMortiseTenon(tenon=rod.left_end, mortise=leg.back_edge))
    return asm


def round_mortise_tenon(
    leg_length: float = 450, rung_length: float = 300, diameter: float = 16
) -> Assembly:
    """A rung with a round tenon (a shoulder all round, its end chamfered)
    in a blind hole in a square leg."""
    asm = Assembly("round_mortise_tenon", root_location=STANDING)
    leg = asm.add(Board("leg", LEG_STOCK, length=leg_length, width=45))
    rung = asm.add(Rod("rung", ROD_OAK, length=rung_length))
    asm.join(
        RoundMortiseTenon(tenon=rung.left_end, mortise=leg.back_edge, diameter=diameter, chamfer=1)
    )
    return asm


def round_tenon_in_round_leg(
    leg_length: float = 450, rung_length: float = 300, diameter: float = 16
) -> Assembly:
    """A stretcher's round tenon in a cross hole in a round leg (its shoulder
    meets the leg along a line, as it would before being scribed to it)."""
    asm = Assembly("round_tenon_in_round_leg", root_location=STANDING)
    leg = asm.add(Rod("leg", ROUND_LEG_OAK, length=leg_length))
    rung = asm.add(Rod("rung", ROD_OAK, length=rung_length))
    asm.join(
        RoundMortiseTenon(tenon=rung.left_end, mortise=leg.back_edge, diameter=diameter, length=25)
    )
    return asm


def through_round_tenon(leg_length: float = 400, diameter: float = 25) -> Assembly:
    """A square leg with a round tenon through a seat, flush with its top."""
    asm = Assembly("through_round_tenon")
    seat = asm.add(Board("seat", THICK_OAK, length=300, width=300))
    leg = asm.add(Board("leg", LEG_STOCK, length=leg_length, width=45))
    asm.join(
        RoundMortiseTenon(
            tenon=leg.right_end, mortise=seat.bottom_face, diameter=diameter, length=30
        )
    )
    return asm


def tapered_round_tenon(
    leg_length: float = 400, diameter: float = 25, tip_diameter: float = 20
) -> Assembly:
    """A round leg with a tapered tenon through a tapered (reamed) hole in a
    seat, as in a Windsor chair (not splayed yet)."""
    asm = Assembly("tapered_round_tenon")
    seat = asm.add(Board("seat", LEG_STOCK, length=300, width=300))
    leg = asm.add(Rod("leg", ROUND_LEG_OAK, length=leg_length))
    asm.join(
        RoundMortiseTenon(
            tenon=leg.right_end,
            mortise=seat.bottom_face,
            diameter=diameter,
            tip_diameter=tip_diameter,
            length=45,
        )
    )
    return asm


def wedged_round_tenon(
    leg_length: float = 400, diameter: float = 25, kerf: float = 2, flare: float = 2
) -> Assembly:
    """A round leg through a stool's seat, held by a wedge in a kerf across
    the grain of the seat.

    The wedge is two thirds of the seat long, at its head as wide as the
    kerf and the spread both ways, and 24 mm thick, so that its corners
    stay within the 25 mm tenon.
    """
    asm = Assembly("wedged_round_tenon")
    seat = asm.add(Board("seat", THICK_OAK, length=300, width=300))
    leg = asm.add(Rod("leg", ROUND_LEG_OAK, length=leg_length))
    wedge_stock = Stock.board(thickness=24, species="oak")
    wedge = asm.add(Board("wedge", wedge_stock, length=20, width=kerf + 2 * flare))
    asm.join(
        WedgedRoundMortiseTenon(
            tenon=leg.right_end, mortise=seat.bottom_face, diameter=diameter, wedge=wedge, kerf=kerf
        )
    )
    return asm


# --- Dowels, pegs and screws ------------------------------------------------


def _dowels(asm: Assembly, prefix: str, count: int, length: float) -> tuple[Rod, ...]:
    return tuple(asm.add(Rod(f"{prefix}_{i + 1}", DOWEL_OAK, length=length)) for i in range(count))


def dowelled_edge_joint(length: float = 500, width: float = 150, stock: Stock = OAK) -> Assembly:
    """Two boards glued edge to edge, aligned by three dowels, 15 mm into each."""
    asm = Assembly("dowelled_edge_joint")
    a = asm.add(Board("a", stock, length=length, width=width))
    b = asm.add(Board("b", stock, length=length, width=width))
    asm.join(Dowels(a.back_edge, b.front_edge, _dowels(asm, "dowel", 3, 30)))
    return asm


def dowelled_frame_corner(
    stile_length: float = 600, rail_length: float = 300, width: float = 60, stock: Stock = OAK
) -> Assembly:
    """A rail butted against the edge of a stile, joined by two dowels
    across its width, 20 mm into each (a dowelled butt joint)."""
    asm = Assembly("dowelled_frame_corner", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    asm.join(Dowels(stile.back_edge, rail.left_end, _dowels(asm, "dowel", 2, 40)))
    return asm


def pinned_mortise_tenon(
    stile_length: float = 600, rail_length: float = 300, width: float = 60, drawbore: float = 0
) -> Assembly:
    """A mortise and tenon pinned by an 8 mm peg through the stile and the
    tenon, flush with both faces of the stile."""
    return _pegged("pinned_mortise_tenon", stile_length, rail_length, width, drawbore)


def drawbored_mortise_tenon(
    stile_length: float = 600, rail_length: float = 300, width: float = 60, drawbore: float = 1.5
) -> Assembly:
    """A drawbored mortise and tenon: the hole in the tenon drilled 1.5 mm
    closer to the shoulder, so the peg pulls the shoulders tight (shown
    assembled, the holes straight)."""
    return _pegged("drawbored_mortise_tenon", stile_length, rail_length, width, drawbore)


def _pegged(
    name: str, stile_length: float, rail_length: float, width: float, drawbore: float
) -> Assembly:
    asm = Assembly(name, root_location=STANDING)
    stile = asm.add(Board("stile", THICK_OAK, length=stile_length, width=width))
    rail = asm.add(Board("rail", THICK_OAK, length=rail_length, width=width))
    peg = asm.add(Rod("peg", DOWEL_OAK, length=THICK_OAK.thickness))
    asm.join(
        PeggedMortiseTenon(
            tenon=rail.left_end,
            mortise=stile.back_edge,
            tenon_length=40,
            peg=peg,
            drawbore=drawbore,
        )
    )
    return asm


def screwed_batten(screw_length: float = 30) -> Assembly:
    """A batten screwed to a board (e.g. the ledge of a door, seen from the
    back), two 4 mm screws in countersunk clearance holes."""
    asm = Assembly("screwed_batten")
    board = asm.add(Board("board", OAK, length=500, width=150))
    batten = asm.add(Board("batten", OAK, length=400, width=60))
    asm.join(Butt(board.top_face, batten.bottom_face, across=CENTERED))
    for end in (batten.left_end, batten.right_end):
        asm.join(Screw(batten.top_face, into=board, length=screw_length, at={end: 40}))
    return asm


def plugged_screws(screw_length: float = 35) -> Assembly:
    """A thick batten screwed to a board, the screws' heads sunk in
    counterbores 8 mm deep, to be closed by plugs."""
    asm = Assembly("plugged_screws")
    board = asm.add(Board("board", OAK, length=500, width=150))
    batten = asm.add(Board("batten", THICK_OAK, length=400, width=60))
    asm.join(Butt(board.top_face, batten.bottom_face, across=CENTERED))
    for end in (batten.left_end, batten.right_end):
        asm.join(
            Screw(
                batten.top_face,
                into=board,
                length=screw_length,
                at={end: 40},
                head_diameter=10,
                counterbore_depth=8,
            )
        )
    return asm
