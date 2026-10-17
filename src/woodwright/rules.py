"""Rules of thumb for default joint dimensions."""

CHISEL_WIDTHS = (3.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0, 25.0)  # mm, a common metric set


def tenon_thickness(stock_thickness: float, chisels: tuple[float, ...] = CHISEL_WIDTHS) -> float:
    """About a third of the stock, snapped up to the nearest chisel width."""
    fitting = [width for width in sorted(chisels) if width >= stock_thickness / 3]
    return fitting[0] if fitting else max(chisels)


def tenon_length(mortise_depth: float) -> float:
    """Two thirds of the material behind the mortised side."""
    return mortise_depth * 2 / 3
