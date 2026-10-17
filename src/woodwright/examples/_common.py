"""Stock and frames shared by the examples."""

import build123d as bd

from woodwright.stock import Stock

OAK = Stock.board(thickness=20, species="oak")

# Boards stand up in the global frame (X = width, Y = depth, Z = up),
# their length along Z.
STANDING = bd.Location(bd.Plane((0, 20, 0), x_dir=(0, 0, 1), z_dir=(0, 1, 0)))
