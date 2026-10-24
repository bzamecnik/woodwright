from pathlib import Path

from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from woodwright.pdf import Page, Plans, draw_sheet, write_plans
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
    write_plans(path, Plans("table", pages, cover=_sheet()))
    pdf = path.read_bytes()
    assert pdf.count(b"/Type /Page\n") == 5  # with the cover and contents
    assert b"/MediaBox [ 0 0 841.8898 708.6614 ]" in pdf  # 297 x 250 mm
    for title in (b"(Assembly)", b"(1  leg)", b"(2  rail)"):  # bookmarks
        assert title in pdf
