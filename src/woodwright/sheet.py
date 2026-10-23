"""A sheet of paper for drawings: lines, text and circles in paper millimetres, as SVG.

Coordinates have their origin at the bottom left of the sheet, y up, so
that drawing coordinates map onto them without flipping; the SVG is written
y down.
"""

import math
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

Point2 = tuple[float, float]

# Line styles: stroke width and dash pattern in mm (ISO 128 line types).
STYLES = {
    "visible": "stroke-width:0.5",
    "hidden": "stroke-width:0.25;stroke-dasharray:2,1",
    "center": "stroke-width:0.18;stroke-dasharray:6,1,1,1",
    "thin": "stroke-width:0.18",
    "frame": "stroke-width:0.35",
}
FONT = "Helvetica, Arial, sans-serif"
TEXT = 2.5  # height of dimension text
TICK = 1.3  # half the length of a dimension's tick mark
GAP = 1.0  # between a part and its extension lines
OVERSHOOT = 1.5  # of extension lines past the dimension line


def text_width(text: str, size: float = TEXT) -> float:
    """An estimate of the width of a line of text (a sans-serif font)."""
    return 0.56 * size * len(text)


@dataclass
class Sheet:
    width: float
    height: float
    items: list[str] = field(default_factory=list)

    def line(self, points: list[Point2], style: str = "thin") -> None:
        if len(points) < 2:
            return
        coords = " ".join(f"{x:.2f},{self.height - y:.2f}" for x, y in points)
        self.items.append(f'<polyline class="{style}" points="{coords}"/>')

    def rect(self, lo: Point2, hi: Point2, style: str = "frame") -> None:
        (x0, y0), (x1, y1) = lo, hi
        self.line([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], style)

    def circle(self, center: Point2, radius: float, style: str = "thin") -> None:
        x, y = center
        self.items.append(
            f'<circle class="{style}" cx="{x:.2f}" cy="{self.height - y:.2f}" '
            f'r="{radius:.2f}" fill="white"/>'
        )

    def text(
        self,
        at: Point2,
        text: str,
        size: float = TEXT,
        anchor: str = "middle",
        angle: float = 0,
        bold: bool = False,
    ) -> None:
        """Text with its baseline at `at`, turned `angle` degrees counterclockwise;
        `anchor` start, middle or end."""
        x, y = at[0], self.height - at[1]
        weight = ' font-weight="bold"' if bold else ""
        rotate = f' transform="rotate({-angle:.2f} {x:.2f} {y:.2f})"' if angle else ""
        self.items.append(
            f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size:g}" '
            f'text-anchor="{anchor}"{weight}{rotate}>{escape(text)}</text>'
        )

    def balloon(self, center: Point2, label: str, radius: float = 2.6) -> None:
        """A number in a circle, marking a feature or a part."""
        self.circle(center, radius)
        self.text((center[0], center[1] - TEXT * 0.36), label)

    def dimension(
        self,
        a: Point2,
        b: Point2,
        line_a: Point2,
        line_b: Point2,
        text: str,
        text_at: Point2 | None = None,
    ) -> None:
        """A linear dimension between `a` and `b` (the origins of the extension
        lines), its dimension line from `line_a` to `line_b`, with oblique
        ticks at the ends and `text` above its middle (or at `text_at`)."""
        for origin, end in ((a, line_a), (b, line_b)):
            d = _sub(end, origin)
            length = math.hypot(*d)
            if length > GAP:
                u = (d[0] / length, d[1] / length)
                self.line([_add(origin, _mul(u, GAP)), _add(end, _mul(u, OVERSHOOT))])
        self.line([line_a, line_b])
        along = _sub(line_b, line_a)
        length = math.hypot(*along) or 1.0
        u = (along[0] / length, along[1] / length)
        tick = _mul(_rotate(u, 45), TICK)
        for p in (line_a, line_b):
            self.line([_sub(p, tick), _add(p, tick)], "visible")
        angle = math.degrees(math.atan2(u[1], u[0]))
        if angle > 90.01 or angle <= -89.99:  # read from the bottom or the right
            angle -= 180 if angle > 0 else -180
        if text_at is None:
            normal = _rotate((1, 0), angle + 90)
            text_at = _add(_mul(_add(line_a, line_b), 0.5), _mul(normal, 0.8))
        self.text(text_at, text, angle=angle)

    def svg(self) -> str:
        style = "\n".join(
            f"  .{name} {{ fill:none; stroke:black; stroke-linecap:round; {css} }}"
            for name, css in STYLES.items()
        )
        return "\n".join(
            [
                '<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{self.width:.1f}mm" height="{self.height:.1f}mm" '
                f'viewBox="0 0 {self.width:.2f} {self.height:.2f}">',
                f"<style>\n{style}\n  text {{ font-family: {FONT}; fill: black; }}\n</style>",
                f'<rect width="{self.width:.2f}" height="{self.height:.2f}" fill="white"/>',
                *self.items,
                "</svg>",
                "",
            ]
        )

    def write(self, path: Path) -> None:
        path.write_text(self.svg())


def _add(a: Point2, b: Point2) -> Point2:
    return a[0] + b[0], a[1] + b[1]


def _sub(a: Point2, b: Point2) -> Point2:
    return a[0] - b[0], a[1] - b[1]


def _mul(a: Point2, k: float) -> Point2:
    return a[0] * k, a[1] * k


def _rotate(a: Point2, degrees: float) -> Point2:
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return a[0] * c - a[1] * s, a[0] * s + a[1] * c
