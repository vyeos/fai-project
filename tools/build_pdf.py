"""Build the final project report as PDF from the shared content source.

Run from the repository root:

    python -X utf8 tools/build_pdf.py

Output: deliverables/final_report.pdf

Mirrors the DOCX house style (tools/build_report.py): Letter pages with 1 inch
margins, a cover page without header or footer, a contents page with page
numbers, navy headings with a hairline rule, navy-banded tables, numbered
captions, a running title header and "Page N" footers. Uses Calibri and
Consolas when the Windows fonts are available, Helvetica and Courier otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.platypus.tableofcontents import TableOfContents

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from report_content import BLOCKS, REPORT_SUBTITLE, REPORT_TITLE  # noqa: E402

OUT = REPO / "deliverables"
OUT.mkdir(exist_ok=True)

NAVY = colors.HexColor("#1F3864")
BLUE = colors.HexColor("#4F81BD")
INK = colors.HexColor("#1F2328")
GREY = colors.HexColor("#595959")
RULE = colors.HexColor("#C9D1DC")
ROW_RULE = colors.HexColor("#D9DEE5")
BAND = colors.HexColor("#F4F6F9")
CODE_BG = colors.HexColor("#F3F4F6")

PAGE_W, PAGE_H = LETTER
MARGIN = inch
TEXT_W = PAGE_W - 2 * MARGIN
REFERENCE = re.compile(r"^\[\d+\]\s*")
NUMERIC = re.compile(r"^[\d\s.,%/()×≈~+−-]+$|^\d")
REGISTER_TITLE = "Appendix C – List of figures and tables"

FONT_DIR = Path("C:/Windows/Fonts")
CHAR_FALLBACKS = {
    "≤": "<=", "≥": ">=", "≈": "~", "→": "->", "−": "-",
    "₂": "2", "₁": "1", "ᵢ": "i", "⁻": "-", "⁹": "9", "₊": "+",
    "α": "alpha", "β": "beta", "τ": "tau", "ρ": "rho", "ℓ": "l", "×": "x", "…": "...",
}


def register_fonts() -> tuple[dict[str, str], TTFont | None]:
    """Use Calibri/Consolas if present; return font names and the body TTF."""
    files = {
        "Calibri": "calibri.ttf", "Calibri-Bold": "calibrib.ttf",
        "Calibri-Italic": "calibrii.ttf", "Calibri-BoldItalic": "calibriz.ttf",
        "Consolas": "consola.ttf",
    }
    if all((FONT_DIR / f).exists() for f in files.values()):
        for name, file in files.items():
            pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))
        pdfmetrics.registerFontFamily(
            "Calibri", normal="Calibri", bold="Calibri-Bold",
            italic="Calibri-Italic", boldItalic="Calibri-BoldItalic",
        )
        names = {"body": "Calibri", "bold": "Calibri-Bold", "italic": "Calibri-Italic",
                 "mono": "Consolas"}
        return names, pdfmetrics.getFont("Calibri")
    names = {"body": "Helvetica", "bold": "Helvetica-Bold", "italic": "Helvetica-Oblique",
             "mono": "Courier"}
    return names, None


FONTS, BODY_TTF = register_fonts()


def sanitise(text: str) -> str:
    """Replace characters the body font cannot draw with readable equivalents."""
    out: list[str] = []
    for ch in text:
        if BODY_TTF is not None:
            drawable = ord(ch) in BODY_TTF.face.charToGlyph
        else:
            try:
                ch.encode("cp1252")
                drawable = True
            except UnicodeEncodeError:
                drawable = False
        out.append(ch if drawable else CHAR_FALLBACKS.get(ch, ""))
    return "".join(out)


def esc(text: str) -> str:
    """Sanitise and escape text for Paragraph (plain text input assumed)."""
    return _xml_escape(sanitise(text)).replace("\n", "<br/>")


def build_styles() -> dict[str, ParagraphStyle]:
    """Paragraph styles matching the DOCX house style."""
    body, bold, italic = FONTS["body"], FONTS["bold"], FONTS["italic"]

    def style(name, **kw):
        base = {"fontName": body, "fontSize": 11, "leading": 14.5, "textColor": INK,
                "spaceAfter": 8}
        base.update(kw)
        return ParagraphStyle(name, **base)

    return {
        "title": style("title", fontName=bold, fontSize=28, leading=32, alignment=TA_CENTER,
                       textColor=colors.black, spaceAfter=10),
        "report": style("report", fontSize=14, leading=18, alignment=TA_CENTER, textColor=GREY,
                        spaceAfter=6),
        "subtitle": style("subtitle", fontName=italic, alignment=TA_CENTER, textColor=GREY,
                          spaceAfter=48),
        "cover_label": style("cover_label", fontName=bold, alignment=TA_RIGHT, textColor=GREY,
                             spaceAfter=0),
        "cover_value": style("cover_value", spaceAfter=0),
        "front": style("front", fontName=bold, fontSize=16, leading=20, textColor=NAVY,
                       spaceAfter=12),
        "h1": style("h1", fontName=bold, fontSize=16, leading=20, textColor=NAVY,
                    spaceBefore=22, spaceAfter=4),
        "h2": style("h2", fontName=bold, fontSize=13, leading=16, textColor=BLUE,
                    spaceBefore=10, spaceAfter=3),
        "p": style("p", alignment=TA_JUSTIFY),
        "note": style("note", fontName=italic, textColor=GREY),
        "bullet": style("bullet", leftIndent=18, bulletIndent=6, spaceAfter=4),
        "caption": style("caption", fontName=italic, fontSize=9.5, leading=12,
                         alignment=TA_CENTER, textColor=GREY, spaceBefore=4, spaceAfter=14),
        "cell": style("cell", fontSize=9.5, leading=11.5, spaceAfter=0),
        "cell_right": style("cell_right", fontSize=9.5, leading=11.5, spaceAfter=0,
                            alignment=TA_RIGHT),
        "cell_head": style("cell_head", fontName=bold, fontSize=9.5, leading=11.5,
                           textColor=colors.white, spaceAfter=0),
        "code": style("code", fontName=FONTS["mono"], fontSize=9, leading=12, spaceAfter=0,
                      backColor=CODE_BG, leftIndent=11, borderPadding=6, spaceBefore=4),
        "toc_note": style("toc_note", fontName=italic, fontSize=8.5, textColor=GREY),
        "register": style("register", leftIndent=65, firstLineIndent=-65, spaceAfter=3),
        "register_head": style("register_head", fontName=bold, spaceBefore=6),
    }


class ReportDoc(BaseDocTemplate):
    """Cover template without decoration; body template with header/footer; TOC hooks."""

    def __init__(self, filename: str) -> None:
        super().__init__(
            filename, pagesize=LETTER, leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=MARGIN, title=REPORT_TITLE,
            author="Rudra Patel, Pruthvi Navadiya", subject=REPORT_SUBTITLE,
        )
        frame = Frame(MARGIN, MARGIN, TEXT_W, PAGE_H - 2 * MARGIN, id="body")
        self.addPageTemplates([
            PageTemplate(id="cover", frames=[frame]),
            PageTemplate(id="body", frames=[frame], onPage=self.decorate),
        ])

    @staticmethod
    def decorate(canvas, doc) -> None:
        """Running title header with a rule, and a centred Page N footer."""
        canvas.saveState()
        canvas.setFont(FONTS["body"], 8.5)
        canvas.setFillColor(GREY)
        top = PAGE_H - 0.6 * inch
        canvas.drawRightString(PAGE_W - MARGIN, top, sanitise(REPORT_TITLE))
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, top - 4, PAGE_W - MARGIN, top - 4)
        canvas.setFont(FONTS["body"], 9)
        canvas.drawCentredString(PAGE_W / 2, 0.55 * inch, f"Page {doc.page}")
        canvas.restoreState()

    def afterFlowable(self, flowable) -> None:  # noqa: N802 - reportlab hook name
        """Feed level-1 headings into the table of contents."""
        if isinstance(flowable, Paragraph) and flowable.style.name == "h1":
            self.notify("TOCEntry", (0, flowable.getPlainText(), self.page))


def heading(text: str, styles) -> list:
    """Level-1 heading with the hairline rule under it."""
    return [
        Paragraph(esc(text), styles["h1"]),
        HRFlowable(width="100%", thickness=0.75, color=RULE, spaceBefore=0, spaceAfter=8),
    ]


def cover(rows, styles) -> list:
    """Cover page flowables."""
    flows = [
        Spacer(1, 150),
        Paragraph(esc(REPORT_TITLE), styles["title"]),
        Paragraph("Project Report", styles["report"]),
        Paragraph(esc(REPORT_SUBTITLE), styles["subtitle"]),
    ]
    data = []
    for label, value in rows:
        values = value if isinstance(value, list) else [value]
        data.append([
            Paragraph(esc(label), styles["cover_label"]),
            Paragraph("<br/>".join(esc(v) for v in values), styles["cover_value"]),
        ])
    table = Table(data, colWidths=[1.7 * inch, 3.6 * inch])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    flows.append(table)
    return flows


def contents(styles) -> list:
    """Contents page with real page numbers (filled by multiBuild)."""
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle(
        "toc1", fontName=FONTS["body"], fontSize=11, leading=14, textColor=INK,
        spaceAfter=5,
    )]
    toc.dotsMinLevel = 0
    return [NextPageTemplate("body"), PageBreak(), Paragraph("Contents", styles["front"]), toc]


def data_table(number: int, caption: str, headers, rows, styles) -> list:
    """Numbered caption above a navy-banded table."""
    numeric = [
        col > 0 and all(NUMERIC.match(str(r[col]).strip() or "x") for r in rows)
        for col in range(len(headers))
    ]
    data = [[Paragraph(esc(h), styles["cell_head"]) for h in headers]]
    for row in rows:
        data.append([
            Paragraph(esc(str(c)), styles["cell_right" if numeric[i] else "cell"])
            for i, c in enumerate(row)
        ])
    # Every column fits its longest word (numeric columns their longest value) on one line;
    # leftover width goes to the columns with the most text.
    def text_width(text: str) -> float:
        return pdfmetrics.stringWidth(sanitise(text), FONTS["bold"], 9.5) + 12

    minimum, ideal = [], []
    for col in range(len(headers)):
        cells = [headers[col]] + [str(r[col]) for r in rows]
        words = [word for cell in cells for word in cell.split()] or [""]
        unbreakable = cells[1:] if numeric[col] else words
        minimum.append(max(text_width(w) for w in unbreakable + headers[col].split()))
        ideal.append(max(text_width(c) for c in cells))
    if sum(ideal) <= TEXT_W:
        col_widths = [w * TEXT_W / sum(ideal) for w in ideal]
    else:
        slack = [i - m for i, m in zip(ideal, minimum, strict=True)]
        spare = max(TEXT_W - sum(minimum), 0)
        total_slack = sum(slack) or 1
        col_widths = [m + spare * s / total_slack for m, s in zip(minimum, slack, strict=True)]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BAND]),
        ("LINEABOVE", (0, 0), (-1, 0), 1, NAVY),
        ("LINEBELOW", (0, -1), (-1, -1), 1, NAVY),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, ROW_RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    title = Paragraph(esc(f"Table {number}. {caption.rstrip('.')}."), styles["caption"])
    return [title, table, Spacer(1, 12)]


def figure(number: int, relpath: str, caption: str, styles) -> KeepTogether:
    """Centred image (max 6 in wide) with a numbered caption below."""
    image_path = REPO / relpath
    if not image_path.exists():
        raise FileNotFoundError(f"missing figure: {image_path}")
    pixel_w, pixel_h = ImageReader(str(image_path)).getSize()
    scale = min(6.0 * inch / pixel_w, 4.4 * inch / pixel_h)
    image = Image(str(image_path), width=pixel_w * scale, height=pixel_h * scale)
    text = Paragraph(esc(f"Figure {number}. {caption.rstrip('.')}."), styles["caption"])
    return KeepTogether([Spacer(1, 6), image, text])


def flowables(styles) -> list:
    """Translate content blocks into platypus flowables."""
    flows: list = []
    figures: list[str] = []
    tables: list[str] = []
    for block in BLOCKS:
        kind = block[0]
        if kind in ("title", "subtitle"):
            continue
        if kind == "cover":
            flows += cover(block[1], styles)
            flows += contents(styles)
        elif kind == "pagebreak":
            flows.append(PageBreak())
        elif kind == "h1":
            if block[1] == "Abstract":
                flows.append(PageBreak())
            flows += heading(block[1], styles)
        elif kind == "h2":
            flows.append(Paragraph(esc(block[1]), styles["h2"]))
        elif kind == "p":
            flows.append(Paragraph(esc(block[1]), styles["p"]))
        elif kind == "note":
            flows.append(Paragraph(esc(block[1]), styles["note"]))
        elif kind == "bullets":
            items = block[1]
            numbered = all(REFERENCE.match(item) for item in items)
            for index, item in enumerate(items, start=1):
                bullet = f"{index}." if numbered else "•"
                flows.append(Paragraph(esc(REFERENCE.sub("", item)), styles["bullet"],
                                       bulletText=bullet))
            flows.append(Spacer(1, 4))
        elif kind == "code":
            # One shaded paragraph keeps the background continuous; &nbsp; keeps alignment.
            lines = [esc(line).replace(" ", "&nbsp;") for line in block[1]]
            flows.append(Paragraph("<br/>".join(lines), styles["code"]))
            flows.append(Spacer(1, 10))
        elif kind == "table":
            tables.append(block[1])
            flows += data_table(len(tables), block[1], block[2], block[3], styles)
        elif kind == "figure":
            figures.append(block[2])
            flows.append(figure(len(figures), block[1], block[2], styles))
        else:  # pragma: no cover
            raise ValueError(f"unknown block kind: {kind}")

    flows += heading(REGISTER_TITLE, styles)
    for label, items in (("Figure", figures), ("Table", tables)):
        flows.append(Paragraph(f"{label}s", styles["register_head"]))
        for number, caption in enumerate(items, start=1):
            flows.append(Paragraph(
                f"{label} {number}&nbsp;&nbsp;&nbsp;&nbsp;{esc(caption.rstrip('.'))}.",
                styles["register"],
            ))
    return flows


def main() -> None:
    """Assemble and save the PDF (two passes so the contents get page numbers)."""
    doc = ReportDoc(str(OUT / "final_report.pdf"))
    doc.multiBuild(flowables(build_styles()))
    print(f"saved {OUT / 'final_report.pdf'}")


if __name__ == "__main__":
    main()
