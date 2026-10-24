from pathlib import Path

from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from woodwright.pdf import (
    STANDARD_FONTS,
    Page,
    Plans,
    _inline,
    _wrap,
    draw_sheet,
    fonts,
    markdown,
    write_plans,
)
from woodwright.sheet import Sheet


def _sheet() -> Sheet:
    sheet = Sheet(297, 210)
    sheet.line([(10, 10), (100, 10), (100, 50)], "hidden")
    sheet.circle((50, 50), 2.6)
    sheet.text((50, 49), "7", anchor="middle")
    sheet.text((20, 100), "ø8 TOP FACE", angle=90, bold=True)
    return sheet


def test_sheet_to_svg_and_pdf(tmp_path: Path) -> None:
    sheet = _sheet()
    svg = sheet.svg()
    assert 'class="hidden" points="10.00,200.00 100.00,200.00 100.00,160.00"' in svg
    assert 'font-weight="bold" transform="rotate(-90.00 20.00 110.00)">ø8 TOP FACE<' in svg

    path = tmp_path / "sheet.pdf"
    canvas = Canvas(str(path), pagesize=(297 * mm, 210 * mm), pageCompression=0)
    draw_sheet(canvas, sheet)
    canvas.showPage()
    canvas.save()
    pdf = path.read_bytes()
    assert pdf.startswith(b"%PDF")
    assert b"[2 1] 0 d" in pdf  # the dashes of a hidden line, in mm
    assert b"(7) Tj" in pdf and rb"(\3708 TOP FACE) Tj" in pdf  # text as text, Latin-1


def test_plans_collate_sheets_of_any_size(tmp_path: Path) -> None:
    path = tmp_path / "plans.pdf"
    pages = [Page("Assembly", _sheet()), Page("1  leg", Sheet(297, 250)), Page("2  rail", _sheet())]
    cut_list = "leg  720 x 60 x 60 mm  oak\n     - mortise 80 x 8 mm, 53 deep, in back_edge"
    write_plans(path, Plans("table", pages, cover=_sheet(), cut_list=cut_list))
    pdf = path.read_bytes()
    assert pdf.count(b"/Type /Page\n") == 6  # with the cover, contents and cut list
    assert b"/MediaBox [ 0 0 841.8898 708.6614 ]" in pdf  # 297 x 250 mm
    for title in (b"(Assembly)", b"(1  leg)", b"(2  rail)", b"(Cut list)"):  # bookmarks
        assert title in pdf


def test_wrap_long_lines_under_their_second_column() -> None:
    line = "leg     810 x 90 x 90 mm  oak, glued up from 2 boards, 4 pieces: front_leg, back_leg"
    assert _wrap(line, 50) == [
        "leg     810 x 90 x 90 mm  oak, glued up from 2",
        "        boards, 4 pieces: front_leg, back_leg",
    ]
    assert _wrap("        - dado 90 mm, 22.5 deep, in top_face", 30) == [
        "        - dado 90 mm, 22.5",
        "          deep, in top_face",
    ]


def test_markdown_subset() -> None:
    text = """
        # Table
        A *solid* top on **wide** aprons, see `buttons` and
        [the plans](https://example.com/?a=1&b=2).

        - legs: 4
          (glued up)
        1. cut the mortises

        ```
        top = Board(...)
        ```
        """
    flowables = markdown(text)
    kinds = [type(f).__name__ for f in flowables]
    assert kinds == ["Paragraph", "Paragraph", "Paragraph", "Paragraph", "Preformatted"]
    heading, paragraph, item, numbered, code = flowables
    assert heading.style.name == "h1"
    assert paragraph.text == (
        "A <i>solid</i> top on <b>wide</b> aprons, see "
        f'<font face="{fonts().mono}">buttons</font> and '
        '<a href="https://example.com/?a=1&amp;b=2" color="blue">the plans</a>.'
    )
    assert item.text == "legs: 4 (glued up)" and item.bulletText == "•"
    assert numbered.bulletText == "1."
    assert code.lines == ["top = Board(...)"]
    assert _inline("snake_case_name and _x_") == "snake_case_name and <i>x</i>"


def test_plans_with_a_description_beyond_latin_1(tmp_path: Path) -> None:
    path = tmp_path / "plans.pdf"
    plans = Plans("stůl", [Page("1  noha", _sheet())], description="Stůl z **dubu**, čep a dlab.")
    write_plans(path, plans)
    pdf = path.read_bytes()
    assert b"(Description)" in pdf
    if fonts() != STANDARD_FONTS:  # a TrueType font was found and embedded
        assert b"/FontFile2" in pdf


def test_wrap_code_under_its_indent() -> None:
    line = "    top = asm.add(Board('top', oak, length=1200, width=600))  # glued up"
    assert _wrap(line, 40, columns=False) == [
        "    top = asm.add(Board('top', oak,",
        "        length=1200, width=600))  #",
        "        glued up",
    ]
