"""Build the final project report as PDF from the shared content source.

Run from the repository root:

    python -X utf8 tools/build_pdf.py

Output: deliverables/final_report.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from report_content import BLOCKS  # noqa: E402

OUT = REPO / "deliverables"
OUT.mkdir(exist_ok=True)

# Same tokens as the dashboard (visualization/__init__.py).
ACCENT = colors.HexColor("#2457d6")
RULE = colors.HexColor("#e2e2dc")
BAND = colors.HexColor("#f6f6f2")
TEXT = colors.HexColor("#17191c")

CHAR_FALLBACKS = {
    "≤": "<=", "≥": ">=", "≈": "~", "→": "->", "−": "-", "–": "-", "—": "-",
    "₂": "_2", "₁": "_1", "ᵢ": "_i", "⁻": "^-", "⁹": "9",
    "α": "alpha", "β": "beta", "τ": "tau", "ρ": "rho",
    "×": "x", "·": ".", "…": "...", "ℓ": "l",
}

SEQUENCE_FALLBACKS = {
    "ᵢ₊₁": "_(i+1)",
    "⁻⁹": "-9",
    "α·W": "alpha*W",
    "β·S": "beta*S",
}


def sanitise(text: str) -> str:
    """Map characters outside cp1252 to readable ASCII equivalents."""
    for old, new in SEQUENCE_FALLBACKS.items():
        text = text.replace(old, new)
    out: list[str] = []
    for ch in text:
        try:
            ch.encode("cp1252")
            out.append(ch)
        except UnicodeEncodeError:
            out.append(CHAR_FALLBACKS.get(ch, ""))
    return "".join(out)


def esc(text: str) -> str:
    """Sanitise and escape text for Paragraph (plain text input assumed)."""
    return _xml_escape(sanitise(text)).replace("\n", "<br/>")


def build_styles() -> dict[str, ParagraphStyle]:
    """Create the paragraph styles used by the report."""
    base = getSampleStyleSheet()
    width = 16 * cm
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontSize=20, leading=24,
            alignment=TA_CENTER, spaceAfter=6, textColor=TEXT,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"], fontSize=11, leading=15,
            alignment=TA_CENTER, spaceAfter=14, textColor=colors.HexColor("#404040"),
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontSize=14, leading=18,
            spaceBefore=14, spaceAfter=6, textColor=TEXT,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontSize=11.5, leading=15,
            spaceBefore=10, spaceAfter=4, textColor=ACCENT,
        ),
        "p": ParagraphStyle(
            "p", parent=base["BodyText"], fontSize=9.5, leading=13.5,
            spaceAfter=6, alignment=4, width=width,
        ),
        "note": ParagraphStyle(
            "note", parent=base["BodyText"], fontSize=9, leading=12.5,
            spaceAfter=6, textColor=colors.HexColor("#595959"), width=width,
        ),  # italics applied at call site
        "bullet": ParagraphStyle(
            "bullet", parent=base["BodyText"], fontSize=9.5, leading=13,
            leftIndent=14, bulletIndent=4, spaceAfter=3,
        ),
        "caption": ParagraphStyle(
            "caption", parent=base["BodyText"], fontSize=8.5, leading=11,
            alignment=TA_CENTER, textColor=colors.HexColor("#595959"),
            spaceBefore=2, spaceAfter=10,
        ),
        "tablecaption": ParagraphStyle(
            "tablecaption", parent=base["BodyText"], fontSize=9, leading=12,
            spaceBefore=4, spaceAfter=3, textColor=colors.HexColor("#404040"),
        ),
        "cell": ParagraphStyle(
            "cell", parent=base["BodyText"], fontSize=8, leading=10.5,
        ),
        "cellheader": ParagraphStyle(
            "cellheader", parent=base["BodyText"], fontSize=8.5, leading=11,
            textColor=colors.white,
        ),
        "code": ParagraphStyle(
            "code", parent=base["BodyText"], fontName="Courier", fontSize=8,
            leading=11, backColor=BAND,
            borderPadding=4, leftIndent=8, spaceAfter=3,
        ),
    }


def make_table(caption: str, headers: list[str], rows: list[list[str]], styles) -> list:
    """Create a styled table with caption, wrapped in KeepTogether when small."""
    data = [[Paragraph(esc(h), styles["cellheader"]) for h in headers]]
    data += [[Paragraph(esc(str(c)), styles["cell"]) for c in row] for row in rows]
    ncols = len(headers)
    total = 16.4 * cm
    # Weight columns by their longest cell text so captions do not overflow.
    weights = []
    for col in range(ncols):
        longest = max([len(headers[col])] + [len(str(r[col])) for r in rows])
        weights.append(max(6, longest))
    norm = sum(weights)
    col_widths = [(w / norm) * total for w in weights]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BAND]),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    caption_paragraph = Paragraph(esc(caption), styles["tablecaption"])
    return [caption_paragraph, table, Spacer(1, 10)]


def flowables(blocks, styles) -> list:
    """Translate content blocks into platypus flowables."""
    flows: list = []
    for block in blocks:
        kind = block[0]
        if kind == "pagebreak":
            flows.append(PageBreak())
        elif kind == "title":
            flows.append(Paragraph(esc(block[1]), styles["title"]))
        elif kind == "subtitle":
            flows.append(Paragraph(esc(block[1]), styles["subtitle"]))
        elif kind == "h1":
            flows.append(Paragraph(esc(block[1]), styles["h1"]))
        elif kind == "h2":
            flows.append(Paragraph(esc(block[1]), styles["h2"]))
        elif kind == "p":
            flows.append(Paragraph(esc(block[1]), styles["p"]))
        elif kind == "note":
            paragraph = Paragraph(
                f"<i>{esc(block[1])}</i>", styles["note"]
            )
            flows.append(paragraph)
        elif kind == "bullets":
            for item in block[1]:
                flows.append(Paragraph(esc(item), styles["bullet"], bulletText="•"))
            flows.append(Spacer(1, 6))
        elif kind == "code":
            flows += [Paragraph(esc(line), styles["code"]) for line in block[1]]
            flows.append(Spacer(1, 6))
        elif kind == "table":
            flows += make_table(block[1], block[2], block[3], styles)
        elif kind == "figure":
            image_path = REPO / block[1]
            if not image_path.exists():
                raise FileNotFoundError(f"missing figure: {image_path}")
            pixel_w, pixel_h = ImageReader(str(image_path)).getSize()
            scale = min(15.5 * cm / pixel_w, 9.6 * cm / pixel_h)
            image = Image(str(image_path), width=pixel_w * scale, height=pixel_h * scale)
            flows.append(KeepTogether([image, Paragraph(esc(block[2]), styles["caption"])]))
        else:  # pragma: no cover
            raise ValueError(f"unknown block kind: {kind}")
    return flows


def decorate(canvas, doc) -> None:
    """Page footer with the report short title and page number."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#808080"))
    canvas.drawCentredString(
        A4[0] / 2, 1.1 * cm,
        f"Classical AI-Based Traffic Signal Coordination — page {doc.page}",
    )
    canvas.restoreState()


def main() -> None:
    """Assemble and save the PDF."""
    styles = build_styles()
    doc = SimpleDocTemplate(
        str(OUT / "final_report.pdf"),
        pagesize=A4,
        leftMargin=1.9 * cm, rightMargin=1.9 * cm,
        topMargin=1.8 * cm, bottomMargin=2.0 * cm,
        title="Classical AI-Based Traffic Signal Coordination",
        author="Rudra Patel, Pruthvi Navadiya",
    )
    doc.build(flowables(BLOCKS, styles), onFirstPage=decorate, onLaterPages=decorate)
    print(f"saved {OUT / 'final_report.pdf'}")


if __name__ == "__main__":
    main()
