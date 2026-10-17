"""Stock and orientations shared by the examples."""

from woodwright.placement import FRONT, LEFT, RIGHT, UP, orient
from woodwright.stock import Stock

OAK = Stock.board(thickness=20, species="oak")
THIN_OAK = Stock.board(thickness=10, species="oak")  # for panels

# A board standing up, its back edge to the right and its reference face
# away from the viewer: a stile, a leg.
STANDING = orient(right_end=UP, back_edge=RIGHT)
# The side of a case standing up, its reference face outside (to the left).
CASE_SIDE = orient(right_end=UP, ref_face=LEFT)
# A board with its length to the right, its reference face towards the
# viewer: the front of a box or a drawer.
BOX_FRONT = orient(right_end=RIGHT, ref_face=FRONT)
