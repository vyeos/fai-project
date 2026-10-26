"""Build the final project report as DOCX from the shared content source.

Run from the repository root:

    python -X utf8 tools/build_report.py

Output: deliverables/final_report.docx
"""

from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from report_content import BLOCKS, REPORT_SUBTITLE, REPORT_TITLE  # noqa: E402

OUT = REPO / "deliverables"
OUT.mkdir(exist_ok=True)


def add_block(doc: Document, block: tuple) -> None:
    """Append one content block to the document."""
    kind = block[0]
    if kind == "pagebreak":
        doc.add_page_break()
    elif kind == "title":
        paragraph = doc.add_paragraph(block[1])
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.runs[0].bold = True
        paragraph.runs[0].font.size = Pt(26)
    elif kind == "subtitle":
        paragraph = doc.add_paragraph(block[1])
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.runs[0].italic = True
        paragraph.runs[0].font.size = Pt(13)
    elif kind == "h1":
        doc.add_heading(block[1], level=1)
    elif kind == "h2":
        doc.add_heading(block[1], level=2)
    elif kind == "p":
        doc.add_paragraph(block[1], style="Normal")
    elif kind == "note":
        paragraph = doc.add_paragraph(block[1])
        paragraph.runs[0].italic = True
    elif kind == "bullets":
        for item in block[1]:
            doc.add_paragraph(item, style="List Bullet")
    elif kind == "code":
        for line in block[1]:
            paragraph = doc.add_paragraph(line)
            paragraph.runs[0].font.name = "Consolas"
            paragraph.runs[0].font.size = Pt(9)
    elif kind == "table":
        caption, headers, rows = block[1], block[2], block[3]
        doc.add_paragraph(caption, style="Caption").runs[0].italic = True
        table = doc.add_table(rows=1 + len(rows), cols=len(headers))
        table.style = "Light Grid Accent 1"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for col, text in enumerate(headers):
            cell = table.rows[0].cells[col]
            cell.text = text
            for run in cell.paragraphs[0].runs:
                run.bold = True
        for row_idx, row in enumerate(rows, start=1):
            for col, text in enumerate(row):
                table.rows[row_idx].cells[col].text = text
        doc.add_paragraph()
    elif kind == "figure":
        relpath, caption = block[1], block[2]
        image_path = REPO / relpath
        if not image_path.exists():
            raise FileNotFoundError(f"missing figure: {image_path}")
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.add_run().add_picture(str(image_path), width=Inches(5.8))
        caption_paragraph = doc.add_paragraph(caption)
        caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        caption_paragraph.runs[0].italic = True
        caption_paragraph.runs[0].font.size = Pt(9)
    else:  # pragma: no cover - grammar regression
        raise ValueError(f"unknown block kind: {kind}")


def main() -> None:
    """Assemble and save the DOCX."""
    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)
    for section in document.sections:
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)

    for index, block in enumerate(BLOCKS):
        if block[0] == "title" and index > 0:
            document.add_page_break()
        add_block(document, block)

    document.core_properties.title = REPORT_TITLE
    document.core_properties.comments = REPORT_SUBTITLE

    output = OUT / "final_report.docx"
    document.save(output)
    print(f"saved {output}")


if __name__ == "__main__":
    main()
