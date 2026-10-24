"""The plans of an assembly as one PDF, with reportlab: its drawing sheets
in order, each a page of its own size, numbered and bookmarked.

A sheet is drawn in its own millimetres (the canvas scaled to mm, y up as
in `Sheet`), so line widths, dashes and text sizes keep their values; lines
stay vectors and text stays text, in the PDF's built-in Helvetica.

The document is laid out by reportlab's Platypus: each sheet is a flowable
filling a page template of the sheet's size.
"""

from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import BaseDocTemplate, Flowable, Frame, NextPageTemplate, PageTemplate
from reportlab.platypus.flowables import PageBreak

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


@dataclass
class Page:
    """A sheet in the plans, under a title in the bookmarks (and contents)."""

    title: str
    sheet: Sheet


def write_plans(path: Path, name: str, pages: list[Page]) -> None:
    """The plans of assembly `name` as a PDF: its sheets in the order given."""
    sizes = sorted({(p.sheet.width, p.sheet.height) for p in pages})
    templates = [_sheet_template(size) for size in sizes]
    doc = _Plans(
        str(path),
        pageTemplates=templates,
        title=f"{name}: plans",
        creator=f"woodwright {version('woodwright')}",
    )
    story: list[Flowable] = []
    for i, page in enumerate(pages):
        story.append(NextPageTemplate(_template_id(page.sheet.width, page.sheet.height)))
        if i:
            story.append(PageBreak())
        story.append(_SheetFlowable(page))
    # the first page's template comes first
    first = _template_id(pages[0].sheet.width, pages[0].sheet.height)
    doc.pageTemplates.sort(key=lambda t: t.id != first)
    doc.build(story)


class _Plans(BaseDocTemplate):
    def afterFlowable(self, flowable: Flowable) -> None:
        """A bookmark for each sheet."""
        if isinstance(flowable, _SheetFlowable):
            key = f"page{self.page}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(flowable.page.title, key, level=0)


class _SheetFlowable(Flowable):
    """A sheet filling its page (a frame of the sheet's size without padding)."""

    def __init__(self, page: Page) -> None:
        super().__init__()
        self.page = page

    def wrap(self, available_width: float, available_height: float) -> tuple[float, float]:
        return self.page.sheet.width * mm, self.page.sheet.height * mm

    def draw(self) -> None:
        draw_sheet(self.canv, self.page.sheet)


def _template_id(width: float, height: float) -> str:
    return f"sheet {width:g}x{height:g}"


def _sheet_template(size: tuple[float, float]) -> PageTemplate:
    width, height = size[0] * mm, size[1] * mm
    frame = Frame(0, 0, width, height, 0, 0, 0, 0, id="sheet")
    return PageTemplate(_template_id(*size), [frame], onPage=_page_number, pagesize=(width, height))


def _page_number(canvas: Canvas, doc: BaseDocTemplate) -> None:
    """The page's number at the bottom of the page, below the sheet's margin."""
    canvas.saveState()
    canvas.setFont(FONTS[False], 8)
    canvas.drawCentredString(doc.pagesize[0] / 2, 5 * mm, str(doc.page))
    canvas.restoreState()
