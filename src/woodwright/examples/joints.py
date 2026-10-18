"""Joints of two boards."""

import itertools

from woodwright import rules
from woodwright.assembly import Assembly
from woodwright.cuts import Groove
from woodwright.examples._common import BOX_FRONT, CASE_SIDE, OAK, SIDE_OAK, STANDING, THIN_OAK
from woodwright.joints import (
    Bridle,
    Butt,
    CrossLap,
    DadoJoint,
    GrooveJoint,
    HalfBlindDovetail,
    HalfLap,
    LooseTenon,
    MitreCorner,
    MitredShoulderTenon,
    MitreSplice,
    MortiseTenon,
    RabbetJoint,
    SlidingDovetail,
    TeeBridle,
    ThroughDovetail,
    TongueAndGroove,
)
from woodwright.part import Board
from woodwright.placement import CENTERED, flush_with, offset
from woodwright.stock import Stock

THICK_OAK = Stock.board(thickness=30, species="oak")  # also 30 x 45 mm (2:3) frame stock
LEG_STOCK = Stock.board(thickness=45, species="oak")


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


def stub_tenon_corner(
    stile_length: float = 300,
    rail_length: float = 200,
    width: float = 60,
    tenon_length: float | None = None,
    outer_shoulder: float = 15,
    stock: Stock = OAK,
) -> Assembly:
    """A frame corner with a stub tenon and three shoulders.

    The tenon has shoulders on both faces and on the outer edge, so the
    mortise is set back from the end of the stile; on the inner edge it is
    flush with the rail. It is blind, by default two thirds of the stile wide.
    """
    asm = Assembly("stub_tenon_corner", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    asm.join(
        MortiseTenon(
            tenon=rail.left_end,
            mortise=stile.back_edge,
            position=flush_with(stile.right_end),
            tenon_length=tenon_length,
            shoulder=(outer_shoulder, 0),  # the front edge is outer, at the end of the stile
        )
    )
    return asm


def haunched_mortise_tenon_corner(
    stile_length: float = 300,
    rail_length: float = 200,
    width: float = 60,
    groove_width: float = 8,
    groove_depth: float = 10,
    stock: Stock = OAK,
) -> Assembly:
    """A frame corner with grooves along the inside edges and a haunched tenon.

    The groove runs out of the end of the stile; the haunch on the outer
    side of the tenon fills it, the tenon being as thick as the groove is wide.
    """
    asm = Assembly("haunched_mortise_tenon_corner", root_location=STANDING)
    stile = asm.add(Board("stile", stock, length=stile_length, width=width))
    rail = asm.add(Board("rail", stock, length=rail_length, width=width))
    for edge in (stile.back_edge, rail.back_edge):
        edge.part.cut(Groove(edge, width=groove_width, depth=groove_depth))
    asm.join(
        MortiseTenon(
            tenon=rail.left_end,
            mortise=stile.back_edge,
            position=flush_with(stile.right_end),
            shoulder=groove_depth,
            tenon_thickness=groove_width,
            haunch=rail.front_edge,
            haunch_length=groove_depth,
        )
    )
    return asm


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
    asm = Assembly("edge_mitre_corner", root_location=CASE_SIDE)
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
