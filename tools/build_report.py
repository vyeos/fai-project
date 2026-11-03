"""Build the final project report as DOCX from the shared content source.

Run from the repository root:

    python -X utf8 tools/build_report.py

Output: deliverables/final_report.docx

Layout follows the team's report house style: US Letter with 1-inch margins, a
cover page without header or footer, a contents page (a Word TOC field), navy
section headings with a hairline rule, navy-banded data tables, numbered figure
and table captions, a running title header, "Page N" footers and a register of
figures and tables as the last appendix.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor, Twips

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from report_content import BLOCKS, REPORT_SUBTITLE, REPORT_TITLE  # noqa: E402

OUT = REPO / "deliverables"
OUT.mkdir(exist_ok=True)

NAVY = "1F3864"
BLUE = "4F81BD"
INK = "1F2328"
GREY = "595959"
RULE = "C9D1DC"
ROW_RULE = "D9DEE5"
BAND = "F4F6F9"
CODE_BG = "F3F4F6"
TEXT_WIDTH_TWIPS = 9360  # 6.5 in between 1 in margins on Letter
REFERENCE = re.compile(r"^\[\d+\]\s*")
NUMERIC = re.compile(r"^[\d\s.,%/()×≈~+−-]+$|^\d")


# ---------------------------------------------------------------- XML helpers


def _el(tag: str, **attrs: str) -> OxmlElement:
    element = OxmlElement(tag)
    for key, value in attrs.items():
        element.set(qn(f"w:{key}"), value)
    return element


def _border(parent, edge: str, val: str, size: int = 4, color: str = RULE, space: int = 0) -> None:
    parent.append(_el(f"w:{edge}", val=val, sz=str(size), space=str(space), color=color))


def _rgb(hex_code: str) -> RGBColor:
    return RGBColor.from_string(hex_code)


def _shade(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_pr.append(_el("w:shd", val="clear", color="auto", fill=fill))


def _field(paragraph, instruction: str, placeholder: str = "") -> None:
    """Insert a Word field (e.g. PAGE, TOC) into ``paragraph``."""
    def run_with(child):
        run = paragraph.add_run()
        run._r.append(child)
        return run

    run_with(_el("w:fldChar", fldCharType="begin"))
    instr = _el("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruction} "
    run_with(instr)
    run_with(_el("w:fldChar", fldCharType="separate"))
    if placeholder:
        paragraph.add_run(placeholder)
    run_with(_el("w:fldChar", fldCharType="end"))


# ---------------------------------------------------------------- styles


def setup_styles(document: Document) -> None:
    """Define the house paragraph styles."""
    styles = document.styles

    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    normal.font.size = Pt(11)
    normal.font.color.rgb = _rgb(INK)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = 1.15

    title = styles["Title"]
    title.font.name = "Calibri"
    title.font.size = Pt(28)
    title.font.bold = True
    title.font.color.rgb = _rgb("000000")
    title.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(10)
    title.paragraph_format.line_spacing = 1.0
    # Drop the default template's bottom border under the title.
    p_pr = title.element.get_or_add_pPr()
    for border in p_pr.findall(qn("w:pBdr")):
        p_pr.remove(border)

    for name, size, color, before, after, rule in (
        ("Heading 1", 16, NAVY, 22, 8, True),
        ("Heading 2", 13, BLUE, 10, 2, False),
    ):
        heading = styles[name]
        fonts = heading.element.rPr.rFonts
        for attr in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
            fonts.attrib.pop(qn(f"w:{attr}"), None)
        heading.font.name = "Calibri"
        heading.font.size = Pt(size)
        heading.font.bold = True
        heading.font.italic = False
        heading.font.color.rgb = _rgb(color)
        heading.paragraph_format.space_before = Pt(before)
        heading.paragraph_format.space_after = Pt(after)
        heading.paragraph_format.keep_with_next = True
        if rule:
            p_pr = heading.element.get_or_add_pPr()
            borders = _el("w:pBdr")
            _border(borders, "bottom", "single", 6, RULE, 4)
            p_pr.append(borders)

    caption = styles["Caption"]
    caption.font.size = Pt(9.5)
    caption.font.bold = False
    caption.font.italic = True
    caption.font.color.rgb = _rgb(GREY)
    caption.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.space_before = Pt(4)
    caption.paragraph_format.space_after = Pt(14)
    caption.paragraph_format.line_spacing = 1.0

    for name in ("List Bullet", "List Number"):
        styles[name].paragraph_format.space_after = Pt(4)

    def custom(name: str):
        style = styles.add_style(name, 1)
        style.base_style = normal
        return style

    front = custom("Front Heading")
    front.font.size = Pt(16)
    front.font.bold = True
    front.font.color.rgb = _rgb(NAVY)
    front.paragraph_format.space_after = Pt(12)

    toc = custom("TOC Entry")
    toc.paragraph_format.space_after = Pt(5)
    toc.paragraph_format.tab_stops.add_tab_stop(
        Twips(TEXT_WIDTH_TWIPS), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS
    )

    code = custom("Code Block")
    code.font.name = "Consolas"
    code.font.size = Pt(9.5)
    code.paragraph_format.space_after = Pt(0)
    code.paragraph_format.line_spacing = 1.0
    code.paragraph_format.left_indent = Twips(216)
    code.element.get_or_add_pPr().append(_el("w:shd", val="clear", color="auto", fill=CODE_BG))

    register = custom("Register Entry")
    register.paragraph_format.space_after = Pt(3)
    register.paragraph_format.left_indent = Twips(1296)
    register.paragraph_format.first_line_indent = Twips(-1296)


def setup_page(document: Document) -> None:
    """Letter page, 1 in margins, title header and Page N footer (not on the cover)."""
    section = document.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, side, Inches(1))
    section.different_first_page_header_footer = True

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    borders = _el("w:pBdr")
    _border(borders, "bottom", "single", 4, RULE)
    header._p.get_or_add_pPr().append(borders)
    run = header.add_run(REPORT_TITLE)
    run.font.size = Pt(8.5)
    run.font.color.rgb = _rgb(GREY)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("Page ")
    _field(footer, "PAGE", "1")
    for run in footer.runs:
        run.font.size = Pt(9)
        run.font.color.rgb = _rgb(GREY)

    # Ask Word to refresh the TOC and page fields on open.
    document.settings.element.append(_el("w:updateFields", val="true"))


# ---------------------------------------------------------------- blocks


def add_cover(document: Document, title: str, subtitle: str, rows) -> None:
    """Cover page: title, subtitle, borderless details table."""
    paragraph = document.add_paragraph(title, style="Title")
    paragraph.paragraph_format.space_before = Twips(3000)
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Pt(6)
    run = paragraph.add_run("Project Report")
    run.font.size = Pt(14)
    run.font.color.rgb = _rgb(GREY)
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Twips(960)
    run = paragraph.add_run(subtitle)
    run.font.size = Pt(11)
    run.font.italic = True
    run.font.color.rgb = _rgb(GREY)

    table = document.add_table(rows=len(rows), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row, (label, value) in zip(table.rows, rows, strict=True):
        row.cells[0].width, row.cells[1].width = Twips(2448), Twips(5184)
        left = row.cells[0].paragraphs[0]
        left.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        left.paragraph_format.space_after = Pt(8)
        run = left.add_run(label)
        run.font.bold = True
        run.font.color.rgb = _rgb(GREY)
        values = value if isinstance(value, list) else [value]
        for index, line in enumerate(values):
            cell = row.cells[1]
            paragraph = cell.paragraphs[0] if index == 0 else cell.add_paragraph()
            paragraph.paragraph_format.space_after = Pt(8 if index == len(values) - 1 else 2)
            paragraph.add_run(line)


def add_contents(document: Document, headings: list[str]) -> None:
    """Contents page: TOC field pre-filled with the section titles."""
    paragraph = document.add_paragraph("Contents", style="Front Heading")
    paragraph.paragraph_format.page_break_before = True
    for index, heading in enumerate(headings):
        paragraph = document.add_paragraph(style="TOC Entry")
        if index == 0:
            paragraph.add_run()._r.append(_el("w:fldChar", fldCharType="begin"))
            instr = _el("w:instrText")
            instr.set(qn("xml:space"), "preserve")
            instr.text = ' TOC \\o "1-1" \\h \\z \\u '
            paragraph.add_run()._r.append(instr)
            paragraph.add_run()._r.append(_el("w:fldChar", fldCharType="separate"))
        paragraph.add_run(heading)
        if index == len(headings) - 1:
            paragraph.add_run()._r.append(_el("w:fldChar", fldCharType="end"))
    note = document.add_paragraph()
    run = note.add_run(
        "Page numbers appear when the document is opened in Microsoft Word "
        "(choose Yes when asked to update fields)."
    )
    run.font.size = Pt(8.5)
    run.font.italic = True
    run.font.color.rgb = _rgb(GREY)


def add_table(document: Document, number: int, caption: str, headers, rows) -> None:
    """Numbered caption above a navy-banded table."""
    document.add_paragraph(f"Table {number}. {caption.rstrip('.')}.", style="Caption")
    table = document.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_pr = table._tbl.tblPr
    borders = _el("w:tblBorders")
    _border(borders, "top", "single", 8, NAVY)
    _border(borders, "left", "nil")
    _border(borders, "bottom", "single", 8, NAVY)
    _border(borders, "right", "nil")
    _border(borders, "insideH", "single", 4, ROW_RULE)
    _border(borders, "insideV", "nil")
    tbl_pr.append(borders)
    margins = _el("w:tblCellMar")
    for edge, width in (("top", 50), ("left", 100), ("bottom", 50), ("right", 100)):
        margins.append(_el(f"w:{edge}", w=str(width), type="dxa"))
    tbl_pr.append(margins)

    # Right-align columns whose body cells are all numeric.
    numeric = [
        col > 0 and all(NUMERIC.match(str(r[col]).strip() or "x") for r in rows)
        for col in range(len(headers))
    ]
    for r_index, row in enumerate(table.rows):
        tr_pr = row._tr.get_or_add_trPr()
        tr_pr.append(_el("w:cantSplit"))
        if r_index == 0:
            tr_pr.append(_el("w:tblHeader"))
        values = headers if r_index == 0 else rows[r_index - 1]
        for c_index, cell in enumerate(row.cells):
            _shade(cell, NAVY if r_index == 0 else (BAND if r_index % 2 == 0 else "FFFFFF"))
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.line_spacing = 1.0
            if numeric[c_index]:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            run = paragraph.add_run(str(values[c_index]))
            run.font.size = Pt(9.5)
            if r_index == 0:
                run.font.bold = True
                run.font.color.rgb = _rgb("FFFFFF")
    document.add_paragraph().paragraph_format.space_after = Pt(4)


def add_figure(document: Document, number: int, relpath: str, caption: str) -> None:
    """Centred 6 in image with a numbered caption below."""
    image_path = REPO / relpath
    if not image_path.exists():
        raise FileNotFoundError(f"missing figure: {image_path}")
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = True
    paragraph.paragraph_format.space_before = Pt(10)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.add_run().add_picture(str(image_path), width=Inches(6.0))
    document.add_paragraph(f"Figure {number}. {caption.rstrip('.')}.", style="Caption")


def add_register(document: Document, figures: list[str], tables: list[str]) -> None:
    """Final appendix listing every figure and table."""
    document.add_heading("Appendix C – List of figures and tables", level=1)
    for label, items in (("Figure", figures), ("Table", tables)):
        heading = document.add_paragraph()
        heading.add_run(f"{label}s").bold = True
        for number, caption in enumerate(items, start=1):
            document.add_paragraph(
                f"{label} {number}\t{caption.rstrip('.')}.", style="Register Entry"
            )


def build(document: Document) -> None:
    """Translate the content blocks into the document."""
    headings = [b[1] for b in BLOCKS if b[0] == "h1"] + ["Appendix C – List of figures and tables"]
    figures: list[str] = []
    tables: list[str] = []
    for block in BLOCKS:
        kind = block[0]
        if kind in ("title", "subtitle"):
            continue
        if kind == "cover":
            add_cover(document, REPORT_TITLE, REPORT_SUBTITLE, block[1])
            add_contents(document, headings)
        elif kind == "pagebreak":
            document.add_page_break()
        elif kind == "h1":
            paragraph = document.add_heading(block[1], level=1)
            if block[1] == "Abstract":
                paragraph.paragraph_format.page_break_before = True
        elif kind == "h2":
            document.add_heading(block[1], level=2)
        elif kind == "p":
            document.add_paragraph(block[1])
        elif kind == "note":
            run = document.add_paragraph().add_run(block[1])
            run.italic = True
            run.font.color.rgb = _rgb(GREY)
        elif kind == "bullets":
            items = block[1]
            if all(REFERENCE.match(item) for item in items):
                for item in items:
                    document.add_paragraph(REFERENCE.sub("", item), style="List Number")
            else:
                for item in items:
                    document.add_paragraph(item, style="List Bullet")
        elif kind == "code":
            for line in block[1]:
                document.add_paragraph(line, style="Code Block")
            document.add_paragraph().paragraph_format.space_after = Pt(4)
        elif kind == "table":
            tables.append(block[1])
            add_table(document, len(tables), block[1], block[2], block[3])
        elif kind == "figure":
            figures.append(block[2])
            add_figure(document, len(figures), block[1], block[2])
        else:  # pragma: no cover - grammar regression
            raise ValueError(f"unknown block kind: {kind}")
    add_register(document, figures, tables)


def main() -> None:
    """Assemble and save the DOCX."""
    document = Document()
    setup_styles(document)
    setup_page(document)
    build(document)
    document.core_properties.title = REPORT_TITLE
    document.core_properties.subject = REPORT_SUBTITLE
    document.core_properties.author = "Rudra Patel, Pruthvi Navadiya"
    output = OUT / "final_report.docx"
    document.save(output)
    print(f"saved {output}")


if __name__ == "__main__":
    main()
