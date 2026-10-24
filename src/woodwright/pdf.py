"""The plans of an assembly as one PDF, with reportlab: a cover, contents,
its drawing sheets in order, each a page of its own size, numbered and
bookmarked.

A sheet is drawn in its own millimetres (the canvas scaled to mm, y up as
in `Sheet`), so line widths, dashes and text sizes keep their values; lines
stay vectors and text stays text, in the PDF's built-in Helvetica.

The document is laid out by reportlab's Platypus: each sheet is a flowable
filling a page template of the sheet's size, text flows in a column on A4;
the contents take a second pass for their page numbers.
"""

import inspect
import os
import re
import textwrap
from dataclasses import dataclass
from functools import cache
from importlib.metadata import version
from pathlib import Path
from typing import NamedTuple
from xml.sax.saxutils import escape

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
)
from reportlab.platypus.tableofcontents import TableOfContents

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
                canvas.setFont(_sheet_font(text, bold), size)
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


def _sheet_font(text: str, bold: bool) -> str:
    """Helvetica, as the SVG; for text beyond Latin-1, a TrueType font."""
    try:
        text.encode("latin-1")
    except UnicodeEncodeError:
        return fonts().bold if bold else fonts().regular
    return FONTS[bold]


def _stroke(canvas: Canvas, style: str) -> None:
    width, dash = STYLES[style]
    canvas.setLineWidth(width)
    canvas.setDash(list(dash) if dash else [])


@dataclass
class Page:
    """A sheet in the plans, under a title in the contents and bookmarks."""

    title: str
    sheet: Sheet


@dataclass
class Plans:
    """What goes into the plans of an assembly, in this order: a cover,
    contents, a description, the drawing sheets, the cut list."""

    name: str
    sheets: list[Page]
    cover: Sheet | None = None
    cut_list: str | None = None  # as `ResolvedModel.cut_list()`
    description: str | None = None  # in Markdown, see `markdown`


def write_plans(path: Path, plans: Plans) -> None:
    """The plans as a PDF; see `Plans` for what goes in."""
    sheets = [plans.cover] if plans.cover else []
    sheets += [page.sheet for page in plans.sheets]
    sizes = sorted({(sheet.width, sheet.height) for sheet in sheets})
    templates = [_sheet_template(size) for size in sizes]
    templates += [_text_template(), _wide_template()]
    doc = _Document(
        str(path),
        pageTemplates=templates,
        title=f"{plans.name}: plans",
        creator=f"woodwright {version('woodwright')}",
    )
    story: list[Flowable] = []
    if plans.cover:
        story += _sheet_page(Page("Cover", plans.cover), [(0, "Cover", False)], first=True)
    story += [NextPageTemplate("text"), *([PageBreak()] if story else [])]
    story += [_Heading("Contents", toc=False), _contents()]
    if plans.description:
        story += [PageBreak(), _Heading("Description"), *markdown(plans.description)]
    for i, page in enumerate(plans.sheets):
        entries = [(0, "Drawings", True)] if i == 0 else []
        story += _sheet_page(page, [*entries, (1, page.title, True)], first=False)
    if plans.cut_list:
        story += [NextPageTemplate("wide"), PageBreak(), _Heading("Cut list")]
        story.append(_monospace(plans.cut_list))
    # the first page's template comes first
    first = sheets[0] if plans.cover else None
    first_id = _template_id(first.width, first.height) if first else "text"
    doc.pageTemplates.sort(key=lambda t: t.id != first_id)
    doc.multiBuild(story)


TEXT_MARGIN = 25 * mm
MONO = 8.5  # size of monospaced text (the cut list), points
MONO_CHARS = int((297 * mm - 2 * TEXT_MARGIN) / (0.6 * MONO))  # per line (Courier)


class Fonts(NamedTuple):
    regular: str
    bold: str
    italic: str
    bold_italic: str
    mono: str


# TrueType fonts covering more than Latin-1 (Czech, Polish...), the first
# found is embedded: Arial (the metrics of Helvetica) on macOS and Windows,
# DejaVu on Linux; the files of regular, bold, italic, bold italic, mono.
_WINDOWS = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
_MAC = Path("/System/Library/Fonts/Supplemental")
FONT_FILES = [
    [_MAC / f for f in ("Arial.ttf", "Arial Bold.ttf", "Arial Italic.ttf", "Arial Bold Italic.ttf")]
    + [_MAC / "Courier New.ttf"],
    [_WINDOWS / f for f in ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf", "cour.ttf")],
    *(
        [
            Path(d) / f
            for f in (
                "DejaVuSans.ttf",
                "DejaVuSans-Bold.ttf",
                "DejaVuSans-Oblique.ttf",
                "DejaVuSans-BoldOblique.ttf",
                "DejaVuSansMono.ttf",
            )
        ]
        for d in (
            "/usr/share/fonts/truetype/dejavu",
            "/usr/share/fonts/TTF",
            "/usr/share/fonts/dejavu",
        )
    ),
]
STANDARD_FONTS = Fonts(
    "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique", "Courier"
)


@cache
def fonts() -> Fonts:
    """The fonts of the text pages: the first TrueType fonts found
    (registered with reportlab), else the PDF's standard ones (Latin-1 only)."""
    for files in FONT_FILES:
        if all(f.is_file() for f in files):
            names = Fonts(*(f"woodwright-{style}" for style in Fonts._fields))
            for name, file in zip(names, files, strict=True):
                pdfmetrics.registerFont(TTFont(name, str(file)))
            pdfmetrics.registerFontFamily(
                names.regular,
                normal=names.regular,
                bold=names.bold,
                italic=names.italic,
                boldItalic=names.bold_italic,
            )
            return names
    return STANDARD_FONTS


@cache
def _styles() -> dict[str, ParagraphStyle]:
    f = fonts()
    body = ParagraphStyle("body", fontName=f.regular, fontSize=10, leading=14, spaceAfter=2 * mm)
    return {
        "heading": ParagraphStyle(
            "heading", fontName=f.bold, fontSize=18, leading=22, spaceAfter=6 * mm
        ),
        "h1": ParagraphStyle(
            "h1", body, fontName=f.bold, fontSize=14, leading=18, spaceBefore=4 * mm
        ),
        "h2": ParagraphStyle(
            "h2", body, fontName=f.bold, fontSize=12, leading=16, spaceBefore=3 * mm
        ),
        "h3": ParagraphStyle("h3", body, fontName=f.bold, spaceBefore=2 * mm),
        "body": body,
        "code": ParagraphStyle(
            "code",
            body,
            fontName=f.mono,
            fontSize=9,
            leading=11.5,
            leftIndent=4 * mm,
            spaceBefore=2 * mm,
        ),
        "mono": ParagraphStyle("mono", fontName=f.mono, fontSize=MONO, leading=MONO * 1.25),
        "toc0": ParagraphStyle(
            "toc0", fontName=f.bold, fontSize=11, leading=16, spaceBefore=2 * mm
        ),
        "toc1": ParagraphStyle(
            "toc1", fontName=f.regular, fontSize=10, leading=14, leftIndent=8 * mm
        ),
    }


class _Document(BaseDocTemplate):
    def afterFlowable(self, flowable: Flowable) -> None:
        """A bookmark, and an entry in the contents, for each sheet and heading."""
        for level, title, toc in getattr(flowable, "entries", ()):
            key = f"entry{len(self._entries)}"
            self._entries.append(key)
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, level=level)
            if toc:
                self.notify("TOCEntry", (level, title, self.page, key))

    def handle_documentBegin(self) -> None:
        self._entries: list[str] = []
        super().handle_documentBegin()


class _SheetFlowable(Flowable):
    """A sheet filling its page (a frame of the sheet's size without padding)."""

    def __init__(self, page: Page, entries: list[tuple[int, str, bool]]) -> None:
        super().__init__()
        self.page = page
        self.entries = entries

    def wrap(self, available_width: float, available_height: float) -> tuple[float, float]:
        return self.page.sheet.width * mm, self.page.sheet.height * mm

    def draw(self) -> None:
        draw_sheet(self.canv, self.page.sheet)


class _Heading(Paragraph):
    def __init__(self, title: str, toc: bool = True) -> None:
        super().__init__(escape(title), _styles()["heading"])
        self.entries = [(0, title, toc)]


def _sheet_page(page: Page, entries: list[tuple[int, str, bool]], first: bool) -> list[Flowable]:
    """A sheet on a new page of its size, with its bookmarks and contents
    entries: (level, title, in the contents)."""
    template = NextPageTemplate(_template_id(page.sheet.width, page.sheet.height))
    return [template, *([] if first else [PageBreak()]), _SheetFlowable(page, entries)]


def markdown(text: str) -> list[Flowable]:
    """Paragraphs from a subset of Markdown: headings (#, ##, ###),
    paragraphs, lists (-, *, 1.), fenced code blocks, and in a line **bold**,
    *italic*, `code` and [links](https://...). The text may be indented as a
    whole (a docstring)."""
    styles = _styles()
    flowables: list[Flowable] = []
    lines = inspect.cleandoc(text).splitlines()
    block: list[str] = []  # lines of the paragraph or list item being read
    bullet: tuple[str, int] | None = None  # of that list item, and its level

    def flush() -> None:
        nonlocal block, bullet
        if block:
            inline = _inline(" ".join(line.strip() for line in block))
            if bullet:
                text, level = bullet
                style = ParagraphStyle(
                    "item",
                    styles["body"],
                    leftIndent=(6 + 5 * level) * mm,
                    spaceAfter=1 * mm,
                    bulletIndent=(2 + 5 * level) * mm,
                )
                flowables.append(Paragraph(inline, style, bulletText=text))
            else:
                flowables.append(Paragraph(inline, styles["body"]))
        block, bullet = [], None

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("```"):
            flush()
            end = next(
                (j for j in range(i + 1, len(lines)) if lines[j].strip().startswith("```")),
                len(lines),
            )
            flowables.append(Preformatted("\n".join(lines[i + 1 : end]), styles["code"]))
            i = end + 1
            continue
        heading = re.match(r"(#{1,3})\s+(.*)", line)
        item = re.match(r"(\s*)([-*+]|\d+[.)])\s+(.*)", line)
        if not line.strip():
            flush()
        elif heading:
            flush()
            flowables.append(Paragraph(_inline(heading[2]), styles[f"h{len(heading[1])}"]))
        elif item:
            flush()
            marker = "\u2022" if item[2] in "-*+" else item[2]
            bullet = (marker, len(item[1]) // 2)
            block = [item[3]]
        else:
            block.append(line)
        i += 1
    flush()
    return flowables


def _inline(text: str) -> str:
    """Markdown within a line as reportlab's paragraph markup."""
    parts = re.split(r"(`[^`]+`)", text)
    out = []
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) > 1:
            out.append(f'<font face="{fonts().mono}">{escape(part[1:-1])}</font>')
            continue
        part = escape(part)
        part = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2" color="blue">\1</a>', part)
        part = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: f"<b>{m[1] or m[2]}</b>", part)
        part = re.sub(r"\*(.+?)\*|(?<!\w)_(.+?)_(?!\w)", lambda m: f"<i>{m[1] or m[2]}</i>", part)
        out.append(part)
    return "".join(out)


def _monospace(text: str) -> Preformatted:
    """Monospaced text, its lines wrapped to the width of a wide page."""
    lines = [wrapped for line in text.splitlines() for wrapped in _wrap(line, MONO_CHARS)]
    return Preformatted("\n".join(lines), _styles()["mono"])


def _wrap(line: str, width: int) -> list[str]:
    """A line wrapped to `width`, continued under its second column (a list
    item's text, a cut list line's size) or its indent."""
    match = re.match(r"\s*(- |\S+\s{2,})?", line)
    indent = " " * match.end() if match.group(1) else " " * (match.end() + 4)
    return textwrap.wrap(line, width, subsequent_indent=indent, drop_whitespace=True) or [""]


def _contents() -> TableOfContents:
    contents = TableOfContents(dotsMinLevel=1)
    contents.levelStyles = [_styles()["toc0"], _styles()["toc1"]]
    return contents


def _template_id(width: float, height: float) -> str:
    return f"sheet {width:g}x{height:g}"


def _sheet_template(size: tuple[float, float]) -> PageTemplate:
    width, height = size[0] * mm, size[1] * mm
    frame = Frame(0, 0, width, height, 0, 0, 0, 0, id="sheet")
    return PageTemplate(_template_id(*size), [frame], onPage=_page_number, pagesize=(width, height))


def _text_template() -> PageTemplate:
    """A4 landscape, a column of text as wide as reads well."""
    width, height = 297 * mm, 210 * mm
    frame = Frame(TEXT_MARGIN, TEXT_MARGIN, 160 * mm, height - 2 * TEXT_MARGIN, id="text")
    return PageTemplate("text", [frame], onPage=_page_number, pagesize=(width, height))


def _wide_template() -> PageTemplate:
    """A4 landscape, a frame as wide as the page (long lines of monospaced text)."""
    width, height = 297 * mm, 210 * mm
    frame = Frame(
        TEXT_MARGIN, TEXT_MARGIN, width - 2 * TEXT_MARGIN, height - 2 * TEXT_MARGIN, id="wide"
    )
    return PageTemplate("wide", [frame], onPage=_page_number, pagesize=(width, height))


def _page_number(canvas: Canvas, doc: BaseDocTemplate) -> None:
    """The page's number at the bottom of the page, below the sheet's margin
    (none on the cover)."""
    if doc.page == 1:
        return
    canvas.saveState()
    canvas.setFont(FONTS[False], 8)
    width = canvas._pagesize[0]  # the page template's, not the document's
    canvas.drawCentredString(width / 2, 5 * mm, str(doc.page))
    canvas.restoreState()
