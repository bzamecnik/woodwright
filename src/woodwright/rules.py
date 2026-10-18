"""Rules of thumb for default joint dimensions."""

CHISEL_WIDTHS = (3.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0, 25.0)  # mm, a common metric set


def tenon_thickness(stock_thickness: float, chisels: tuple[float, ...] = CHISEL_WIDTHS) -> float:
    """About a third of the stock, snapped up to the nearest chisel width."""
    fitting = [width for width in sorted(chisels) if width >= stock_thickness / 3]
    return fitting[0] if fitting else max(chisels)


def tenon_length(mortise_depth: float) -> float:
    """Two thirds of the material behind the mortised side."""
    return mortise_depth * 2 / 3


def _round(length: float, step: float = 0.5) -> float:
    """To a length that can be set on a tool."""
    return round(length / step) * step


def dado_depth(stock_thickness: float) -> float:
    """A third of the housing board."""
    return _round(stock_thickness / 3)


def rabbet_depth(stock_thickness: float) -> float:
    """Half of the rabbeted board."""
    return _round(stock_thickness / 2)


def groove_depth(stock_thickness: float) -> float:
    """Half of the stock thickness, a common depth for panel grooves and tongues."""
    return _round(stock_thickness / 2)


def lap_thickness(stock_thickness: float) -> float:
    """Half of the stock: the two laps together make up its thickness."""
    return _round(stock_thickness / 2)


def dovetail_thickness(stock_thickness: float) -> float:
    """Of a sliding dovetail's tongue at the shoulder: half of the stock."""
    return _round(stock_thickness / 2)


def dovetail_lap(stock_thickness: float) -> float:
    """Of the pin board of half-blind dovetails, left in front of the tails: a quarter."""
    return _round(stock_thickness / 4)


def finger_width(stock_thickness: float) -> float:
    """Of the fingers of a box joint: as wide as the stock is thick."""
    return _round(stock_thickness)
