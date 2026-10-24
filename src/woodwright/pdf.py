"""Drawing sheets onto PDF pages, with reportlab.

A sheet is drawn in its own millimetres (the canvas scaled to mm, y up as
in `Sheet`), so line widths, dashes and text sizes keep their values; lines
stay vectors and text stays text, in the PDF's built-in Helvetica.
"""

from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from woodwright.sheet import STYLES, Circle, Line, Sheet, Text

FONTS = {False: "Helvetica", True: "Helvetica-Bold"}


def draw_sheet(canvas: Canvas, sheet: Sheet) -> None:
    """Draw a sheet onto the current page of `canvas`, its bottom left corner
    at the page's."""
    canvas.saveState()
    canvas.scale(mm, mm)
    canvas.setLineCap(1)  # round, as the SVG
    canvas.setLineJoin(1)
    for item in sheet.items:
        match item:
            case Line(points, style):
                _stroke(canvas, style)
                path = canvas.beginPath()
                path.moveTo(*points[0])
                for point in points[1:]:
                    path.lineTo(*point)
                canvas.drawPath(path, stroke=1, fill=0)
            case Circle((x, y), radius, style, fill):
                _stroke(canvas, style)
                canvas.setFillColor(fill)
                canvas.circle(x, y, radius, stroke=1, fill=1)
            case Text((x, y), text, size, anchor, angle, bold):
                canvas.saveState()
                canvas.setFillColor("black")
                canvas.setFont(FONTS[bold], size)
                canvas.translate(x, y)
                if angle:
                    canvas.rotate(angle)
                draw = {
                    "start": canvas.drawString,
                    "middle": canvas.drawCentredString,
                    "end": canvas.drawRightString,
                }[anchor]
                draw(0, 0, text)
                canvas.restoreState()
    canvas.restoreState()


def _stroke(canvas: Canvas, style: str) -> None:
    width, dash = STYLES[style]
    canvas.setLineWidth(width)
    canvas.setDash(list(dash) if dash else [])
