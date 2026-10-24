"""A sheet of paper for drawings: lines, text and circles in paper millimetres.

Coordinates have their origin at the bottom left of the sheet, y up, so
that drawing coordinates map onto them without flipping; the SVG is written
y down. The items are kept as data, rendered to SVG here and onto a PDF page
by `woodwright.pdf`.
"""

import math
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

Point2 = tuple[float, float]

# Line styles: stroke width and dash pattern in mm (ISO 128 line types),
# visible and hidden lines also in thinner weights for dense views.
STYLES: dict[str, tuple[float, tuple[float, ...]]] = {
    "visible": (0.5, ()),
    "visible-m": (0.35, ()),
    "visible-s": (0.25, ()),
    "hidden": (0.25, (2, 1)),
    "hidden-s": (0.18, (1.5, 0.75)),
    "center": (0.18, (6, 1, 1, 1)),
    "thin": (0.18, ()),
    "frame": (0.35, ()),
}
FONT = "Helvetica, Arial, sans-serif"
TEXT = 2.5  # height of dimension text
TICK = 1.3  # half the length of a dimension's tick mark
GAP = 1.0  # between a part and its extension lines
OVERSHOOT = 1.5  # of extension lines past the dimension line


def text_width(text: str, size: float = TEXT) -> float:
    """An estimate of the width of a line of text (a sans-serif font)."""
    return 0.56 * size * len(text)


@dataclass(frozen=True)
class Line:
    points: list[Point2]
    style: str


@dataclass(frozen=True)
class Circle:
    center: Point2
    radius: float
    style: str
    fill: str


@dataclass(frozen=True)
class Text:
    at: Point2  # the start, middle or end of the baseline, as `anchor`
    text: str
    size: float
    anchor: str  # start, middle or end
    angle: float  # degrees counterclockwise
    bold: bool


Item = Line | Circle | Text


@dataclass
class Sheet:
    width: float
    height: float
    items: list[Item] = field(default_factory=list)

    def line(self, points: list[Point2], style: str = "thin") -> None:
        if len(points) < 2:
            return
        self.items.append(Line(points, style))

    def rect(self, lo: Point2, hi: Point2, style: str = "frame") -> None:
        (x0, y0), (x1, y1) = lo, hi
        self.line([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], style)

    def circle(
        self, center: Point2, radius: float, style: str = "thin", fill: str = "white"
    ) -> None:
        self.items.append(Circle(center, radius, style, fill))

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
        self.items.append(Text(at, text, size, anchor, angle, bold))

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
            f"  .{name} {{ fill:none; stroke:black; stroke-linecap:round; {_css(*style)} }}"
            for name, style in STYLES.items()
        )
        return "\n".join(
            [
                '<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{self.width:.1f}mm" height="{self.height:.1f}mm" '
                f'viewBox="0 0 {self.width:.2f} {self.height:.2f}">',
                f"<style>\n{style}\n  text {{ font-family: {FONT}; fill: black; }}\n</style>",
                f'<rect width="{self.width:.2f}" height="{self.height:.2f}" fill="white"/>',
                *(self._svg_item(item) for item in self.items),
                "</svg>",
                "",
            ]
        )

    def _svg_item(self, item: Item) -> str:
        match item:
            case Line(points, style):
                coords = " ".join(f"{x:.2f},{self.height - y:.2f}" for x, y in points)
                return f'<polyline class="{style}" points="{coords}"/>'
            case Circle((x, y), radius, style, fill):
                return (
                    f'<circle class="{style}" cx="{x:.2f}" cy="{self.height - y:.2f}" '
                    f'r="{radius:.2f}" style="fill:{fill}"/>'
                )
            case Text((x, y), text, size, anchor, angle, bold):
                y = self.height - y
                weight = ' font-weight="bold"' if bold else ""
                rotate = f' transform="rotate({-angle:.2f} {x:.2f} {y:.2f})"' if angle else ""
                return (
                    f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size:g}" '
                    f'text-anchor="{anchor}"{weight}{rotate}>{escape(text)}</text>'
                )
        raise TypeError(item)

    def write(self, path: Path) -> None:
        path.write_text(self.svg())


def _css(width: float, dash: tuple[float, ...]) -> str:
    css = f"stroke-width:{width:g}"
    return css + f";stroke-dasharray:{','.join(f'{d:g}' for d in dash)}" if dash else css


def _add(a: Point2, b: Point2) -> Point2:
    return a[0] + b[0], a[1] + b[1]


def _sub(a: Point2, b: Point2) -> Point2:
    return a[0] - b[0], a[1] - b[1]


def _mul(a: Point2, k: float) -> Point2:
    return a[0] * k, a[1] * k


def _rotate(a: Point2, degrees: float) -> Point2:
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return a[0] * c - a[1] * s, a[0] * s + a[1] * c
