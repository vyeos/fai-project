"""Build the read-along presentation as PPTX.

Run from the repository root:

    python -X utf8 tools/build_slides.py

Output: deliverables/final_slides.pptx

The deck is written for a reader who has not studied AI before and is meant
to be read next to the dashboard: every slide carries an "On the website" tag
naming the page and section that shows the same idea live. Colours follow the
dashboard tokens (visualization/__init__.py). Numbers are measured: the
default road comes from a live dashboard run, benchmark rows from
experiments/results/summary.md. Speaker notes are attached to each slide.
"""

from __future__ import annotations

import re
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "deliverables"
OUT.mkdir(exist_ok=True)


def _rgb(hex_code: str) -> RGBColor:
    return RGBColor.from_string(hex_code.lstrip("#"))


# Dashboard tokens.
BG = _rgb("#f6f6f2")
SURFACE = _rgb("#ffffff")
SUNKEN = _rgb("#efefea")
LINE = _rgb("#e2e2dc")
TEXT = _rgb("#17191c")
MUTED = _rgb("#565b63")
FAINT = _rgb("#8b9097")
ACCENT = _rgb("#2457d6")
ACCENT_SOFT = _rgb("#e6ecfa")
GREEN = _rgb("#1e9a5a")
GREEN_SOFT = _rgb("#e3f2ea")
RED = _rgb("#d6433b")
RED_SOFT = _rgb("#f9e6e4")
WARN_SOFT = _rgb("#fbf0dc")
FORWARD = _rgb("#2f6f8f")
REVERSE = _rgb("#c0682a")
GREY = _rgb("#b5b8bd")
SLATE = _rgb("#5d6670")

FONT = "Segoe UI"
FONT_BOLD = "Segoe UI Semibold"

S_W, S_H = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.6)
CONTENT_W = S_W - 2 * MARGIN
TOP = Inches(1.75)
TEXT_INSET = Inches(0.08)
ARROW_H = Inches(0.32)
TABLE_ROW_H = Inches(0.42)
BAR_ROW_H = Inches(0.36)
BAR_LABEL_W = Inches(1.0)


# ---------------------------------------------------------------- primitives


def new_deck() -> Presentation:
    """Create the 16:9 presentation shell."""
    deck = Presentation()
    deck.slide_width = S_W
    deck.slide_height = S_H
    return deck


def rect(slide, x, y, w, h, fill=SURFACE, line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06):
    """Add a filled box; ``line=None`` draws no border."""
    box = slide.shapes.add_shape(shape, x, y, w, h)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        box.adjustments[0] = radius
    box.fill.solid()
    box.fill.fore_color.rgb = fill
    if line is None:
        box.line.fill.background()
    else:
        box.line.color.rgb = line
        box.line.width = Pt(0.75)
    box.shadow.inherit = False
    box.text_frame.text = ""
    return box


def _add_runs(paragraph, text: str, size: float, color: RGBColor, bold: bool, font: str) -> None:
    """Add ``text`` to ``paragraph``; ``**x**`` spans become bold accent-free runs."""
    for i, piece in enumerate(re.split(r"\*\*", text)):
        if not piece:
            continue
        run = paragraph.add_run()
        run.text = piece
        strong = bold or i % 2 == 1
        run.font.name = FONT_BOLD if strong else font
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.bold = False


def text(
    slide, x, y, w, h, paragraphs, size=16, color=TEXT, bold=False, align=PP_ALIGN.LEFT,
    anchor=MSO_ANCHOR.TOP, spacing=6, bullets=False, font=FONT, line_spacing=1.12,
):
    """Text box with one or more paragraphs (str or list[str])."""
    if isinstance(paragraphs, str):
        paragraphs = [paragraphs]
    box = slide.shapes.add_textbox(x, y, w, h)
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    frame.margin_left = frame.margin_right = 0
    frame.margin_top = frame.margin_bottom = 0
    for i, content in enumerate(paragraphs):
        paragraph = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        paragraph.alignment = align
        paragraph.line_spacing = line_spacing
        if i:
            paragraph.space_before = Pt(spacing)
        if bullets:
            _add_runs(paragraph, "•  ", size, ACCENT, True, font)
        _add_runs(paragraph, content, size, color, bold, font)
    return box


def fill_text(shape, paragraphs, size=14, color=TEXT, bold=False, align=PP_ALIGN.CENTER,
              anchor=MSO_ANCHOR.MIDDLE, margin=TEXT_INSET):
    """Write text inside an existing shape."""
    if isinstance(paragraphs, str):
        paragraphs = [paragraphs]
    frame = shape.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    frame.margin_left = frame.margin_right = margin
    frame.margin_top = frame.margin_bottom = Inches(0.04)
    for i, content in enumerate(paragraphs):
        paragraph = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        paragraph.alignment = align
        _add_runs(paragraph, content, size, color, bold, FONT)


def line(slide, x1, y1, x2, y2, color=LINE, width=1.25):
    """Straight connector."""
    connector = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    connector.line.color.rgb = color
    connector.line.width = Pt(width)
    return connector


def arrow(slide, x, y, w, h=ARROW_H, color=FAINT):
    """Right-pointing block arrow."""
    shape = rect(slide, x, y, w, h, fill=color, line=None, shape=MSO_SHAPE.RIGHT_ARROW)
    return shape


def pill(slide, x, y, label, fill=ACCENT_SOFT, color=ACCENT, size=11, w=None):
    """Small rounded tag."""
    width = w or Emu(int(Inches(0.2) + Pt(size) * 0.56 * len(label)))
    shape = rect(slide, x, y, width, Inches(0.32), fill=fill, line=None, radius=0.5)
    fill_text(shape, label, size=size, color=color, bold=True, margin=Inches(0.06))
    return shape


def picture(slide, relpath: str, x, y, w=None, h=None, crop=(0.0, 0.0, 0.0, 0.0)):
    """Screenshot with a thin border; ``crop`` = (left, top, right, bottom) fractions."""
    path = REPO / relpath
    if not path.exists():
        raise FileNotFoundError(f"missing image: {path}")
    pic = slide.shapes.add_picture(str(path), x, y)
    left, top, right, bottom = crop
    aspect = (pic.width * (1 - left - right)) / (pic.height * (1 - top - bottom))
    pic.crop_left, pic.crop_top, pic.crop_right, pic.crop_bottom = crop
    if w is not None:
        pic.width, pic.height = w, Emu(int(w / aspect))
    else:
        pic.width, pic.height = Emu(int(h * aspect)), h
    pic.line.color.rgb = LINE
    pic.line.width = Pt(0.75)
    return pic


def notes(slide, body: str) -> None:
    """Attach speaker notes."""
    slide.notes_slide.notes_text_frame.text = body


# ---------------------------------------------------------------- slide frames


class Deck:
    """Slide factory that numbers slides and stamps the shared frame."""

    def __init__(self) -> None:
        self.prs = new_deck()
        self.count = 0

    def slide(self, part: str, title: str, web: str | None = None, lede: str | None = None):
        """Content slide: part kicker, title, optional lede and website tag."""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.count += 1
        rect(slide, 0, 0, S_W, S_H, fill=BG, line=None, shape=MSO_SHAPE.RECTANGLE)
        text(slide, MARGIN, Inches(0.42), Inches(8), Inches(0.3), part.upper(), size=11,
             color=ACCENT, bold=True)
        text(slide, MARGIN, Inches(0.7), CONTENT_W, Inches(0.6), title, size=28, bold=True).name = "Title"
        if lede:
            text(slide, MARGIN, Inches(1.28), Inches(11.4), Inches(0.4), lede, size=14, color=MUTED)
        line(slide, MARGIN, S_H - Inches(0.5), S_W - MARGIN, S_H - Inches(0.5))
        text(slide, MARGIN, S_H - Inches(0.4), Inches(6), Inches(0.3),
             "Classical AI traffic signal coordination", size=10, color=FAINT)
        text(slide, S_W - MARGIN - Inches(0.6), S_H - Inches(0.4), Inches(0.6), Inches(0.3),
             str(self.count), size=10, color=FAINT, align=PP_ALIGN.RIGHT)
        if web:
            label = f"On the website  ›  {web}"
            width = Emu(int(Inches(0.3) + Pt(10.5) * 0.55 * len(label)))
            pill(slide, S_W - MARGIN - width, Inches(0.38), label, size=10.5, w=width)
        return slide

    def divider(self, number: str, title: str, subtitle: str):
        """Section divider slide."""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.count += 1
        rect(slide, 0, 0, S_W, S_H, fill=SURFACE, line=None, shape=MSO_SHAPE.RECTANGLE)
        rect(slide, 0, 0, Inches(0.22), S_H, fill=ACCENT, line=None, shape=MSO_SHAPE.RECTANGLE)
        text(slide, Inches(1.2), Inches(2.3), Inches(3), Inches(1.2), number, size=66,
             color=ACCENT, bold=True)
        text(slide, Inches(1.2), Inches(3.55), Inches(10.5), Inches(0.9), title, size=40,
             bold=True).name = "Title"
        text(slide, Inches(1.2), Inches(4.45), Inches(10.5), Inches(1.0), subtitle, size=18,
             color=MUTED)
        return slide


def card(slide, x, y, w, h, title, body, tag=None, tag_tone="accent", title_size=16,
         body_size=13, fill=SURFACE, border=LINE):
    """Titled card: heading, optional tag, body paragraphs."""
    rect(slide, x, y, w, h, fill=fill, line=border)
    pad = Inches(0.22)
    title_y = y + Inches(0.2)
    if tag:
        tones = {
            "accent": (ACCENT_SOFT, ACCENT), "green": (GREEN_SOFT, GREEN),
            "red": (RED_SOFT, RED), "grey": (SUNKEN, MUTED), "warn": (WARN_SOFT, _rgb("#8a5a12")),
        }
        bg, fg = tones[tag_tone]
        pill(slide, x + pad, title_y, tag, fill=bg, color=fg, size=10)
        title_y += Inches(0.45)
    text(slide, x + pad, title_y, w - 2 * pad, Inches(0.4), title, size=title_size, bold=True)
    text(slide, x + pad, title_y + Inches(0.42), w - 2 * pad, h - (title_y - y) - Inches(0.5),
         body, size=body_size, color=MUTED, spacing=5)


def table(slide, x, y, w, headers, rows, col_widths=None, size=12, row_h=TABLE_ROW_H,
          highlight_col=None):
    """Light table matching the dashboard's plan table."""
    shape = slide.shapes.add_table(1 + len(rows), len(headers), x, y, w, row_h * (1 + len(rows)))
    tbl = shape.table
    tbl.first_row = True
    tbl.horz_banding = False
    if col_widths:
        total = sum(col_widths)
        for i, cw in enumerate(col_widths):
            tbl.columns[i].width = Emu(int(w * cw / total))
    for r in range(1 + len(rows)):
        tbl.rows[r].height = row_h
        for c in range(len(headers)):
            cell = tbl.cell(r, c)
            value = headers[c] if r == 0 else rows[r - 1][c]
            cell.fill.solid()
            cell.fill.fore_color.rgb = SUNKEN if r == 0 else SURFACE
            cell.margin_left = cell.margin_right = Inches(0.1)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            frame = cell.text_frame
            frame.word_wrap = True
            paragraph = frame.paragraphs[0]
            colour = MUTED if r == 0 else (ACCENT if c == highlight_col else TEXT)
            _add_runs(paragraph, str(value), size, colour, r == 0 or c == highlight_col, FONT)
    return tbl


def traffic_light(slide, x, y, state: str, scale=1.0):
    """Tiny traffic-light glyph: state 'red' or 'green'."""
    w, h = Inches(0.34 * scale), Inches(0.7 * scale)
    rect(slide, x, y, w, h, fill=_rgb("#2a2e33"), line=None, radius=0.3)
    d = Inches(0.2 * scale)
    for i, colour in enumerate(("red", "green")):
        on = colour == state
        fill = (RED if colour == "red" else GREEN) if on else _rgb("#4a4f56")
        rect(slide, x + (w - d) / 2, y + Inches(0.1 * scale) + i * Inches(0.3 * scale), d, d,
             fill=fill, line=None, shape=MSO_SHAPE.OVAL)


def signal_bars(slide, x, y, w, offsets, cycle=60, green=30, horizon=180, row_h=BAR_ROW_H,
                label_w=BAR_LABEL_W, labels=None):
    """Draw green/red timing bars, one row per light (like the dashboard timeline)."""
    bar_w = w - label_w
    for i, offset in enumerate(offsets):
        ry = y + i * (row_h + Inches(0.12))
        name = labels[i] if labels else f"Light {i + 1}"
        text(slide, x, ry, label_w, row_h, name, size=11, color=MUTED, anchor=MSO_ANCHOR.MIDDLE)
        t = 0.0
        while t < horizon:
            phase = (t - offset) % cycle
            is_green = phase < green
            end = t + ((green - phase) if is_green else (cycle - phase))
            end = min(end, horizon)
            sx = x + label_w + Emu(int(bar_w * t / horizon))
            ex = x + label_w + Emu(int(bar_w * end / horizon))
            if ex > sx:
                rect(slide, sx, ry + Inches(0.06), ex - sx, row_h - Inches(0.12),
                     fill=GREEN if is_green else RED, line=None, shape=MSO_SHAPE.RECTANGLE)
            t = end
    axis_y = y + len(offsets) * (row_h + Inches(0.12))
    for tick in range(0, horizon + 1, 30):
        tx = x + label_w + Emu(int(bar_w * tick / horizon))
        text(slide, tx - Inches(0.3), axis_y, Inches(0.6), Inches(0.25), f"{tick} s", size=9,
             color=FAINT, align=PP_ALIGN.CENTER)
    return x + label_w, bar_w


# ---------------------------------------------------------------- the deck


def build() -> Presentation:
    """Assemble the deck."""
    d = Deck()

    # 1. Title -------------------------------------------------------------
    s = d.prs.slides.add_slide(d.prs.slide_layouts[6])
    d.count += 1
    rect(s, 0, 0, S_W, S_H, fill=BG, line=None, shape=MSO_SHAPE.RECTANGLE)
    pill(s, MARGIN, Inches(1.2), "FOUNDATIONS OF AI  ·  APPLIED AI PROJECT", size=11)
    text(s, MARGIN, Inches(1.8), Inches(8.2), Inches(1.8),
         "Timing traffic lights with classical AI", size=44, bold=True,
         line_spacing=1.0).name = "Title"
    text(s, MARGIN, Inches(3.55), Inches(7.6), Inches(1.2),
         "How a constraint-satisfaction search finds when each light should turn green, "
         "so cars hit as few red lights as possible.", size=18, color=MUTED)
    text(s, MARGIN, Inches(5.0), Inches(7.6), Inches(1.4), [
        "**Rudra Patel** (2410111118)  ·  **Pruthvi Navadiya** (2410111071)",
        "ECSCT24301 Foundation of AI  ·  Adani University  ·  AY 2026–27",
        "Supervisor: [placeholder]  ·  Date: [placeholder]",
    ], size=13, color=MUTED, spacing=4)
    # five lights motif
    for i, state in enumerate(("green", "green", "green", "green", "green")):
        traffic_light(s, Inches(9.0) + i * Inches(0.75), Inches(2.4), state, scale=1.2)
    line(s, Inches(8.8), Inches(3.4), Inches(12.7), Inches(3.4), color=GREY, width=3)
    text(s, Inches(8.8), Inches(3.6), Inches(3.9), Inches(0.8),
         "A green wave: every light turns green just as the cars from the light before arrive.",
         size=12, color=MUTED, align=PP_ALIGN.CENTER)
    notes(s, (
        "This deck is meant to be read next to the website. Every slide has a blue tag in the top "
        "right that tells you which page and section of the dashboard shows the same idea. Open "
        "the dashboard (python -m streamlit run app.py) and keep it beside the slides."
    ))

    # 2. How to read this deck ---------------------------------------------
    s = d.slide("Start here", "How to read this deck with the website",
                lede="Open the dashboard next to these slides. The website has four pages, read left to right.")
    pages = [
        ("Try it", "Describe a road and get the best timings, the savings per car and a "
                   "picture of the traffic.", "Slides 4–7, 26–27"),
        ("How it works", "The problem, seven words, how a plan is scored and how the search "
                         "works, with your numbers.", "Slides 5, 13–23"),
        ("Experiments", "Five saved test roads and a live comparison that varies one thing "
                        "at a time.", "Slide 28"),
        ("Under the hood", "Was the answer double-checked, how much searching it took, the "
                           "search step by step.", "Slides 21–24, 29"),
    ]
    cw = (CONTENT_W - 3 * Inches(0.25)) / 4
    for i, (name, body, where) in enumerate(pages):
        x = MARGIN + i * (cw + Inches(0.25))
        card(s, x, TOP + Inches(0.2), cw, Inches(2.6), name, body, tag=f"Page {i + 1}")
        text(s, x + Inches(0.22), TOP + Inches(2.35), cw, Inches(0.3), where, size=11, color=ACCENT,
             bold=True)
    rect(s, MARGIN, Inches(5.05), CONTENT_W, Inches(1.45), fill=SURFACE, line=LINE)
    text(s, MARGIN + Inches(0.3), Inches(5.25), Inches(3.2), Inches(1.1),
         "The deck is in six parts", size=16, bold=True)
    text(s, MARGIN + Inches(3.3), Inches(5.22), Inches(8.5), Inches(1.2), [
        "**1** The problem   **2** What AI means in this course   **3** FAI vocabulary",
        "**4** How AI is built into the project   **5** Results   **6** Limits and recap",
    ], size=14, color=MUTED, spacing=8)
    pill(s, MARGIN, Inches(4.62), "On the website  ›  Page › Section", size=10.5)
    text(s, MARGIN + Inches(3.0), Inches(4.65), Inches(5.5), Inches(0.3),
         "This tag on each slide tells you where to look.", size=12, color=MUTED)
    notes(s, (
        "Read the slides in order. When a slide shows the 'On the website' tag, switch to that page "
        "and scroll to the named section: the website shows the same idea with live numbers. The "
        "default road on the website is the one used throughout this deck."
    ))

    # ---------------------------------------------------------------- Part 1
    s = d.divider("1", "The problem", "Why cars keep stopping at red lights, and what we want to fix.")
    notes(s, "Part 1 explains the real-world problem in plain words before any AI is introduced.")

    # 4. Everyday problem
    s = d.slide("Part 1 · The problem", "Red light, drive, red light again",
                web="Try it › headline",
                lede="One straight road with five traffic lights, 400 m apart, speed limit 40 km/h.")
    road_y = Inches(3.35)
    line(s, MARGIN + Inches(0.3), road_y, S_W - MARGIN - Inches(0.3), road_y, color=GREY, width=8)
    xs = [MARGIN + Inches(0.5) + i * Inches(2.72) for i in range(5)]
    for i, x in enumerate(xs):
        traffic_light(s, x, Inches(2.35), "red" if i else "green")
        text(s, x - Inches(0.3), Inches(3.55), Inches(0.95), Inches(0.3), f"Light {i + 1}",
             size=12, bold=True, align=PP_ALIGN.CENTER)
        if i < 4:
            text(s, x + Inches(0.5), Inches(2.95), Inches(1.9), Inches(0.3), "400 m · 36 s drive",
                 size=11, color=MUTED, align=PP_ALIGN.CENTER)
    stats = [
        ("86.5 s", "average waiting per car when the lights are not coordinated"),
        ("4.0", "stops per car: almost every light is red when the car gets there"),
        ("40", "cars in the test: 20 driving up the road, 20 driving down"),
    ]
    sw = (CONTENT_W - 2 * Inches(0.25)) / 3
    for i, (value, label) in enumerate(stats):
        x = MARGIN + i * (sw + Inches(0.25))
        rect(s, x, Inches(4.35), sw, Inches(1.85))
        text(s, x + Inches(0.25), Inches(4.5), sw, Inches(0.7), value, size=34, bold=True,
             color=RED if i < 2 else TEXT)
        text(s, x + Inches(0.25), Inches(5.25), sw - Inches(0.5), Inches(0.8), label, size=13,
             color=MUTED)
    notes(s, (
        "Picture driving down a city road: you pass one green light and then hit red at every light "
        "after it. On our default road, with the lights not coordinated, an average car waits 86.5 "
        "seconds and stops 4 times on a 5-light trip. That wasted time, fuel and braking is the "
        "problem the project solves. On the website, the 'Try it' page headline says 'waits 14 s "
        "instead of 86 s': the 86 is this number."
    ))

    # 5. Why it happens
    s = d.slide("Part 1 · The problem", "Why it happens: every light turns green together",
                web="How it works › The problem")
    gx, gw = signal_bars(s, MARGIN, TOP + Inches(0.1), Inches(7.3), [0, 0, 0, 0, 0])
    car_x = gx + Emu(int(gw * 36 / 180))
    line(s, car_x, TOP, car_x, TOP + Inches(2.5), color=TEXT, width=1.5)
    text(s, car_x - Inches(1.2), TOP + Inches(2.75), Inches(2.4), Inches(0.5),
         "36 s: car reaches Light 2", size=11, color=TEXT, align=PP_ALIGN.CENTER, bold=True)
    card(s, Inches(8.3), TOP + Inches(0.1), Inches(4.43), Inches(4.4), "What goes wrong", [
        "Each light repeats a **60 s cycle**: 30 s green, 30 s red.",
        "With no coordination all five lights are green from 0 to 30 s.",
        "A car leaving Light 1 at 0 s needs **36 s** to reach Light 2.",
        "At 36 s Light 2 is already **red**. The car stops and waits until 60 s.",
        "The same thing happens at Light 3, 4 and 5.",
    ], body_size=14)
    text(s, MARGIN, Inches(5.55), Inches(7.3), Inches(0.7),
         "Green bar = light is green, red bar = light is red. Every row is the same, so the "
         "lights are not helping each other.", size=12, color=MUTED)
    notes(s, (
        "This is the core of the problem. The timing bars show 3 minutes of five lights that all "
        "start green at the same moment. Driving between lights takes 36 seconds, but the green "
        "only lasts 30 seconds, so a car always arrives just after its light turned red. The "
        "'How it works' page opens with exactly this explanation, using your road's numbers."
    ))

    # 6. The fix
    s = d.slide("Part 1 · The problem", "The fix: delay each light's green (a green wave)",
                web="Try it › When each light turns green")
    signal_bars(s, MARGIN, TOP + Inches(0.1), Inches(7.3), [0, 40, 10, 40, 15],
                labels=["Light 1  +0", "Light 2  +40", "Light 3  +10", "Light 4  +40", "Light 5  +15"],
                label_w=Inches(1.25))
    card(s, Inches(8.3), TOP + Inches(0.1), Inches(4.43), Inches(4.4), "The idea", [
        "Shift each light's green later by a few seconds, the **offset**.",
        "The list of offsets is the **timing plan**. Light 1 is always +0.",
        "The plan on the left is the one our AI found: **0, +40, +10, +40, +15 s**.",
        "Now most cars in both directions arrive while the light is green.",
        "Waiting per car drops from **86.5 s to 13.5 s**.",
    ], body_size=14)
    text(s, MARGIN, Inches(5.55), Inches(7.3), Inches(0.7),
         "Each row is shifted right compared with the one before: that shift is the delay.",
         size=12, color=MUTED)
    notes(s, (
        "The fix is not to change how long lights stay green, only WHEN each one starts. That start "
        "time, measured from Light 1, is called the offset. One offset per light is a timing plan. "
        "The 'Try it' page shows this plan as animated lights and a table that compares each "
        "offset with the 36 s driving time. Why +40 and not +36? Because cars drive in both "
        "directions and the plan has to suit both; slide 7 explains why that is hard."
    ))

    # 7. Why hard
    s = d.slide("Part 1 · The problem", "Why we need AI: too many plans to check by hand",
                web="How it works › Unknowns and their choices")
    rows = [
        ("Choices per light", "12", "offsets 0, 5, 10, … 55 s (a 5 s step)"),
        ("Lights to decide", "4", "Light 1 is fixed at 0"),
        ("Possible plans, 5 lights", "12⁴ = 20,736", "every combination"),
        ("Possible plans, 7 lights", "12⁶ ≈ 3 million", "grows ×12 for every light"),
        ("1 s step instead of 5 s", "60⁴ ≈ 13 million", "finer choices explode the count"),
    ]
    table(s, MARGIN, TOP + Inches(0.1), Inches(7.4), ["", "Count", "Why"], rows,
          col_widths=[3.2, 2.4, 3.6], size=13, row_h=Inches(0.55), highlight_col=1)
    card(s, Inches(8.3), TOP + Inches(0.1), Inches(4.43), Inches(4.4), "Two more reasons", [
        "**Directions fight.** A plan that is perfect for cars going up the road is usually bad "
        "for cars coming down.",
        "**Effects interact.** Changing Light 3 changes when cars reach Light 4 and 5, so you "
        "cannot pick each light on its own.",
        "So we need a **systematic search** that is guaranteed to find the best plan without "
        "trying every one blindly. That is classical AI.",
    ], body_size=14)
    notes(s, (
        "This slide is the bridge to AI. Each light has 12 possible offsets, so five lights give "
        "20,736 different plans, and seven lights give almost 3 million. On top of that, the two "
        "directions want different plans and every light affects the next. We want the BEST plan "
        "and a PROOF that it is best, which is exactly what classical AI search gives us."
    ))

    # ---------------------------------------------------------------- Part 2
    s = d.divider("2", "What 'AI' means in this course",
                  "Foundations of AI is about agents that solve problems by searching and reasoning, "
                  "not about training neural networks.")
    notes(s, "Part 2 explains what kind of AI this is, so the vocabulary in Part 3 makes sense.")

    # 9. Classical vs ML
    s = d.slide("Part 2 · AI in this course", "Classical AI vs machine learning")
    card(s, MARGIN, TOP + Inches(0.1), Inches(5.85), Inches(3.9), "Classical AI  (this project)", [
        "The problem is written down exactly: the unknowns, their choices and the rules.",
        "A search algorithm explores the choices and **proves** which one is best.",
        "No training data, no learning, no guessing. Same input → same answer.",
        "Course topics: agents, search, heuristics, **constraint satisfaction**, logic.",
    ], tag="What we use", tag_tone="accent", body_size=14, border=ACCENT)
    card(s, MARGIN + Inches(6.28), TOP + Inches(0.1), Inches(5.85), Inches(3.9),
         "Machine learning  (not used here)", [
             "Learns patterns from lots of example data, for example camera footage of traffic.",
             "Gives a good guess, usually without a guarantee it is the best.",
             "Needs data we do not have and is hard to explain step by step.",
             "Useful for prediction; overkill when the rules are known.",
         ], tag="Not used", tag_tone="grey", body_size=14)
    text(s, MARGIN, Inches(5.95), CONTENT_W, Inches(0.6),
         "Rule of thumb: when you can write down the rules and the goal exactly, classical search "
         "can find the best answer and prove it.", size=14, color=TEXT, bold=True)
    notes(s, (
        "People often hear 'AI' and think of ChatGPT or self-driving cars, which use machine "
        "learning. Foundations of AI starts earlier: with problems you can describe exactly, solved "
        "by searching through possibilities in a smart way. Our project is entirely classical AI. "
        "There is no training data and no randomness in the answer: the same road always gives the "
        "same plan."
    ))

    # 10. Agent / PEAS
    s = d.slide("Part 2 · AI in this course", "Our project as an AI agent (PEAS)",
                lede="An agent perceives its environment and acts to reach a goal. PEAS lists its four parts.")
    peas = [
        ("P", "Performance measure", "The **score**: total waiting seconds + 2 × number of stops. "
                                     "Lower is better."),
        ("E", "Environment", "A simulated straight road with N lights and a fixed set of cars "
                             "driving both ways."),
        ("A", "Actuators", "Setting the **offset** of each light, which is the timing plan."),
        ("S", "Sensors", "The simulator's report for a plan: each car's waiting time and stops."),
    ]
    pw = (CONTENT_W - 3 * Inches(0.25)) / 4
    for i, (letter, name, body) in enumerate(peas):
        x = MARGIN + i * (pw + Inches(0.25))
        rect(s, x, TOP + Inches(0.15), pw, Inches(3.3))
        text(s, x + Inches(0.25), TOP + Inches(0.3), pw, Inches(0.8), letter, size=40, bold=True,
             color=ACCENT)
        text(s, x + Inches(0.25), TOP + Inches(1.15), pw - Inches(0.4), Inches(0.4), name, size=16,
             bold=True)
        text(s, x + Inches(0.25), TOP + Inches(1.6), pw - Inches(0.45), Inches(1.8), body, size=13,
             color=MUTED)
    rect(s, MARGIN, Inches(5.35), CONTENT_W, Inches(1.1), fill=ACCENT_SOFT, line=None)
    text(s, MARGIN + Inches(0.3), Inches(5.5), CONTENT_W - Inches(0.6), Inches(0.9),
         "Honest note: it is a **planning agent**. It works out the best plan ahead of time inside "
         "a simulator; it is not wired to real traffic lights or cameras.", size=14)
    notes(s, (
        "PEAS is the standard way the textbook (Russell and Norvig) describes an AI agent. Our agent's "
        "goal is the lowest score. Its world is the simulated road. Its only action is choosing the "
        "offsets. What it 'sees' is the simulator's result for each plan. Say clearly that it plans "
        "offline: it does not control real lights."
    ))

    # 11. Environment properties
    s = d.slide("Part 2 · AI in this course", "What kind of environment is it?",
                lede="The textbook classifies environments. Ours is the easiest kind, which is why exact search works.")
    props = [
        ("Fully observable", "The agent knows everything: every car, every distance, every light."),
        ("Deterministic", "The same plan always gives the same result. No randomness in scoring."),
        ("Static", "Nothing changes while the agent is thinking."),
        ("Discrete", "Offsets come in fixed 5 s steps, so there is a finite list of plans."),
        ("Single agent", "One planner decides all the lights. No opponent."),
        ("Known", "The rules of the road (the simulator) are fully written down."),
    ]
    pw = (CONTENT_W - 2 * Inches(0.25)) / 3
    for i, (name, body) in enumerate(props):
        x = MARGIN + (i % 3) * (pw + Inches(0.25))
        y = TOP + Inches(0.15) + (i // 3) * Inches(1.95)
        card(s, x, y, pw, Inches(1.75), name, body, body_size=13)
    text(s, MARGIN, Inches(5.95), CONTENT_W, Inches(0.5),
         "Because of these properties, a plan's score can be computed exactly, and a complete "
         "search can prove a plan is the best one.", size=14, bold=True)
    notes(s, (
        "These six words come straight from the textbook's chapter on environments. Real traffic is "
        "messier (partially observable, random), but our simulated road is fully observable, "
        "deterministic, static, discrete and known. That simplification is what lets us use exact "
        "search and claim 'proven best'. Slide 31 lists what we gave up."
    ))

    # ---------------------------------------------------------------- Part 3
    s = d.divider("3", "FAI vocabulary",
                  "The technical words you will hear, each paired with the plain word the website uses.")
    notes(s, "Part 3 is a glossary. Keep it open during the viva; the right column is what the website says.")

    # 13. CSP terms
    s = d.slide("Part 3 · Vocabulary", "Constraint satisfaction problem (CSP) words",
                web="How it works › Words used on this site")
    rows = [
        ("CSP", "A problem described as unknowns, their allowed values and rules", "“a puzzle with rules”"),
        ("Variable", "One unknown to decide: the offset of Light 2, 3, 4, 5", "Offset (delay)"),
        ("Domain", "Values a variable may take: {0, 5, 10, …, 55} s", "Timing step, 12 choices"),
        ("Constraint", "A rule the values must obey: within ±10 s of a perfect green wave", "Green-wave rule"),
        ("Assignment", "A value for some variables (partial) or for all (complete)", "Timing plan"),
        ("Objective", "Number to minimise: J = waiting + 2 × stops", "Score (lower is better)"),
        ("Optimal", "No other allowed plan has a lower score", "Best possible"),
    ]
    table(s, MARGIN, TOP + Inches(0.05), CONTENT_W, ["FAI term", "Meaning in this project", "Website word"],
          rows, col_widths=[2.0, 6.4, 3.0], size=13, row_h=Inches(0.56), highlight_col=2)
    notes(s, (
        "A CSP, constraint satisfaction problem, is the main AI idea in the project. It has "
        "variables (the offsets), domains (the 12 allowed values each) and constraints (the "
        "green-wave rule). We add an objective, the score, so we are not just looking for ANY "
        "allowed plan but the best one; textbooks call this a constraint optimisation problem. The "
        "right column is the plain word used on the website's glossary."
    ))

    # 14. Search terms
    s = d.slide("Part 3 · Vocabulary", "Search words",
                web="How it works › How the optimized search works")
    rows = [
        ("Search tree", "Every way of choosing offsets light by light, drawn as a tree", "Tree of choices"),
        ("Node", "One partial plan inside the tree", "Branch explored"),
        ("Branching factor", "Children per node: 12 offsets, or 4 once the rule is applied", "Choices per light"),
        ("Depth", "How many lights have been decided so far", "Light being timed"),
        ("Backtracking", "Depth-first search that steps back to try the next value", "Backtracking"),
        ("Complete", "Always finds a solution if one exists", "—"),
        ("Exhaustive / brute force", "Score every single plan, one by one", "Checked by brute force"),
    ]
    table(s, MARGIN, TOP + Inches(0.05), CONTENT_W, ["FAI term", "Meaning in this project", "Website word"],
          rows, col_widths=[2.6, 6.0, 2.8], size=13, row_h=Inches(0.56), highlight_col=2)
    notes(s, (
        "Search means exploring possibilities in an organised way. Picture a tree: the root is an "
        "empty plan, the first level picks Light 2's offset, the next level Light 3's, and so on. A "
        "leaf is a complete plan. Backtracking walks this tree depth-first. Complete means it never "
        "misses a solution; optimal means the answer it returns is the best."
    ))

    # 15. Pruning terms
    s = d.slide("Part 3 · Vocabulary", "Pruning and strategy words",
                web="Under the hood › How much searching it took")
    rows = [
        ("Pruning", "Skipping parts of the tree that cannot contain the answer", "Ruled out / skipped"),
        ("Forward checking", "After fixing a light, cross out next light's values that break a rule", "Ruled out ahead"),
        ("Dead end", "A light is left with no allowed value, so step back at once", "Dead ends"),
        ("Branch and bound", "Remember the best plan so far; skip branches that cannot beat it", "Skipped by bound"),
        ("Bound / heuristic", "Optimistic estimate of the cost still to come", "The estimate"),
        ("Admissible", "The estimate never over-estimates, so pruning is always safe", "Safe but cautious"),
        ("Greedy", "Make the locally best choice once, never reconsider", "Simple green wave"),
        ("Baseline", "Simple reference strategy to compare against", "No coordination"),
    ]
    table(s, MARGIN, TOP + Inches(0.05), CONTENT_W, ["FAI term", "Meaning in this project", "Website word"],
          rows, col_widths=[2.4, 6.4, 2.6], size=12.5, row_h=Inches(0.5), highlight_col=2)
    notes(s, (
        "Pruning is what makes search smart rather than brute force: whole branches of the tree are "
        "cut off without being explored. Forward checking cuts values that break the rule. Branch "
        "and bound cuts branches that cannot beat the best plan found so far, using an estimate "
        "called a bound. If the estimate never over-estimates it is admissible, which guarantees we "
        "never cut the true best plan."
    ))

    # ---------------------------------------------------------------- Part 4
    s = d.divider("4", "How AI is built into the project",
                  "From a road description to a proven-best timing plan, step by step.")
    notes(s, "Part 4 follows one run of the website from input to answer.")

    # 17. Pipeline
    s = d.slide("Part 4 · Integration", "The pipeline: what happens when you press the button",
                web="Try it › Find the best timings")
    steps_ = [
        ("1  Describe", "Lights, distance, speed, traffic", "config.py"),
        ("2  Create cars", "40 cars, both ways, same for every strategy", "scenario_generator.py"),
        ("3  Strategies", "No coordination · green wave · CSP search", "algorithms/"),
        ("4  Score plans", "Simulator drives every car under a plan", "simulator.py"),
        ("5  Double-check", "Brute force scores every allowed plan", "verification.py"),
        ("6  Show", "Plan, savings, diagrams, counters", "dashboard/"),
    ]
    bw = Inches(1.82)
    gap = (CONTENT_W - 6 * bw) / 5
    for i, (name, body, module) in enumerate(steps_):
        x = MARGIN + i * (bw + gap)
        ai = i in (2, 3, 4)
        rect(s, x, TOP + Inches(0.3), bw, Inches(2.3), fill=ACCENT_SOFT if ai else SURFACE,
             line=ACCENT if ai else LINE)
        text(s, x + Inches(0.15), TOP + Inches(0.45), bw - Inches(0.3), Inches(0.4), name, size=14,
             bold=True)
        text(s, x + Inches(0.15), TOP + Inches(0.95), bw - Inches(0.3), Inches(1.0), body, size=12,
             color=MUTED)
        text(s, x + Inches(0.15), TOP + Inches(2.15), bw - Inches(0.3), Inches(0.3), module, size=10,
             color=ACCENT, font="Consolas")
        if i < 5:
            arrow(s, x + bw + Inches(0.03), TOP + Inches(1.3), gap - Inches(0.06), Inches(0.28))
    text(s, MARGIN, TOP + Inches(2.8), Inches(8), Inches(0.3),
         "Blue boxes = the AI part: search, scoring and verification.", size=12, color=ACCENT,
         bold=True)
    card(s, MARGIN, Inches(5.05), CONTENT_W, Inches(1.4), "One shared simulator is the key design choice", [
        "All three strategies are scored by the **same simulator on the same cars**, so any "
        "difference in score comes from the plan alone. Everything is deterministic, so every "
        "number in this deck can be reproduced exactly.",
    ], body_size=13)
    notes(s, (
        "This is how AI is integrated. You describe a road on the Try it page. The program creates "
        "a fixed set of cars, runs the three strategies, and every candidate plan is scored by the "
        "same simulator. The CSP search is the AI that chooses the plan; the simulator is how it "
        "measures plans; the verifier independently checks the answer. The file names are in "
        "src/traffic_coordination/."
    ))

    # 18. Our CSP
    s = d.slide("Part 4 · Integration", "Our problem written as a CSP",
                web="How it works › How the optimized search works")
    rows = [
        ("Variables", "O₂, O₃, O₄, O₅  (Light 1: O₁ = 0)", "Offsets of Lights 2 to 5"),
        ("Domains", "{0, 5, 10, …, 55} s  →  12 values each", "12 choices per light"),
        ("Constraint", "Oᵢ₊₁ within ±10 s of Oᵢ + 36 s (wrapping round 60 s)", "Green-wave rule ±10 s"),
        ("Objective", "minimise  J = W + 2 × S", "Score"),
        ("Search space", "12⁴ = 20,736 plans; rule leaves 4⁴ = 256", "Possible plans / plans scored"),
    ]
    table(s, MARGIN, TOP + Inches(0.05), Inches(8.1), ["CSP part", "Our road", "Website"], rows,
          col_widths=[1.6, 4.4, 2.6], size=13, row_h=Inches(0.62))
    card(s, Inches(9.05), TOP + Inches(0.05), Inches(3.68), Inches(3.75), "Why fix Light 1 at 0?", [
        "Only the **differences** between offsets matter. Shifting every light by the same "
        "amount changes nothing.",
        "Fixing O₁ = 0 removes those duplicates, so the search space is 12 times smaller.",
    ], body_size=13)
    text(s, MARGIN, Inches(5.95), CONTENT_W, Inches(0.5),
         "W = total seconds all cars wait at red lights.  S = total number of stops.  "
         "The rule can be switched off on the website (set it to 0).", size=12, color=MUTED)
    notes(s, (
        "This is the formal CSP. Four variables, twelve values each, one rule per pair of "
        "neighbouring lights, and an objective. The rule says each light's offset should be close "
        "(within 10 s) to the previous light's offset plus the driving time, which is what a green "
        "wave would be. It keeps plans sensible and the search small: 256 allowed plans instead of "
        "20,736."
    ))

    # 19. Score & simulator
    s = d.slide("Part 4 · Integration", "How a plan is scored (the simulator)",
                web="How it works › How a plan is scored")
    rules = [
        ("Create the traffic", "40 cars enter in a bunch, 1 s apart. Same cars for every plan."),
        ("Arrive at a light", "Green when it arrives? It drives straight through."),
        ("Wait at red", "Red? It waits for green. The wait is added and counts as one stop."),
        ("Drive on", "36 s to the next light, always at the speed limit."),
        ("Add it up", "Sum waiting and stops over every car and every light."),
    ]
    for i, (name, body) in enumerate(rules):
        y = TOP + Inches(0.05) + i * Inches(0.8)
        circle = rect(s, MARGIN, y, Inches(0.5), Inches(0.5), fill=ACCENT, line=None, shape=MSO_SHAPE.OVAL)
        fill_text(circle, str(i + 1), size=14, color=SURFACE, bold=True, margin=0)
        text(s, MARGIN + Inches(0.7), y - Inches(0.02), Inches(6.4), Inches(0.3), name, size=15, bold=True)
        text(s, MARGIN + Inches(0.7), y + Inches(0.3), Inches(6.4), Inches(0.4), body, size=12.5, color=MUTED)
    rect(s, Inches(8.0), TOP + Inches(0.05), Inches(4.73), Inches(3.95))
    text(s, Inches(8.3), TOP + Inches(0.25), Inches(4.2), Inches(0.4), "The score, worked out", size=16, bold=True)
    text(s, Inches(8.3), TOP + Inches(0.8), Inches(4.2), Inches(3.0), [
        "**Score = waiting + 2 × stops**",
        "No coordination:  3,460 + 2 × 160 = **3,780**",
        "Optimized plan:  540 + 2 × 39 = **618**",
        "A stop costs 2 extra seconds because braking and pulling away waste time and fuel even "
        "when the wait is short.",
    ], size=13, color=MUTED, spacing=10)
    text(s, MARGIN, Inches(6.05), CONTENT_W, Inches(0.4),
         "Simplified on purpose: no queues, constant speed, one road. See slide 31.", size=12, color=MUTED)
    notes(s, (
        "The simulator is the environment model, the 'rules of the world' the agent uses to judge a "
        "plan. It follows these five rules. The score combines total waiting and total stops. "
        "Checking the arithmetic: uncoordinated cars wait 3,460 seconds in total with 160 stops, "
        "giving 3,780. The optimized plan has 540 seconds and 39 stops, giving 618."
    ))

    # 20. Baselines
    s = d.slide("Part 4 · Integration", "Strategies 1 and 2: the comparisons",
                web="How it works › Three strategies")
    card(s, MARGIN, TOP + Inches(0.05), Inches(5.85), Inches(3.95), "No coordination", [
        "Every offset is 0, so every light turns green together.",
        "No intelligence at all. It shows what the road is like today and what coordination is worth.",
        "Plan: 0, 0, 0, 0, 0  →  score **3,780**",
    ], tag="Baseline", tag_tone="grey", body_size=14)
    card(s, MARGIN + Inches(6.28), TOP + Inches(0.05), Inches(5.85), Inches(3.95), "Simple green wave", [
        "Each light gets the previous offset + the 36 s driving time, rounded to 5 s.",
        "Light 2: 36 → **35**.  Light 3: 35 + 36 = 71 → wraps past 60 → 11 → **10**.",
        "Decides each light once and never reconsiders: a **greedy** method.",
        "Great for cars going up the road, poor for cars coming down. Plan 0, 35, 10, 45, 20 → score **830**.",
    ], tag="Greedy rule of thumb", tag_tone="grey", body_size=14)
    text(s, MARGIN, Inches(5.9), CONTENT_W, Inches(0.6),
         "Neither strategy searches. The third one does, and it beats or ties both on every test road.",
         size=14, bold=True)
    notes(s, (
        "We compare against two simple strategies. 'No coordination' is the baseline. The 'simple "
        "green wave' is a greedy heuristic used by traffic engineers: it is fast and good for one "
        "direction, but it ignores cars going the other way. On one test road (H1) the greedy "
        "plan was even worse than no coordination. The website works through the greedy arithmetic "
        "with your own road."
    ))

    # 21. Backtracking tree
    s = d.slide("Part 4 · Integration", "Strategy 3, step 1: backtracking search",
                web="Under the hood › The search, step by step")
    root_x = Inches(3.6)
    root = rect(s, root_x, TOP + Inches(0.05), Inches(1.4), Inches(0.5), fill=SUNKEN, line=LINE)
    fill_text(root, "Light 1 = 0", size=12, bold=True)
    l2 = [("30", False), ("35", False), ("40", True), ("45", False)]
    l2_y = TOP + Inches(1.15)
    for i, (value, chosen) in enumerate(l2):
        x = MARGIN + Inches(0.1) + i * Inches(1.9)
        line(s, root_x + Inches(0.7), TOP + Inches(0.55), x + Inches(0.6), l2_y, color=GREY)
        node = rect(s, x, l2_y, Inches(1.2), Inches(0.46), fill=ACCENT_SOFT if chosen else SURFACE,
                    line=ACCENT if chosen else LINE)
        fill_text(node, f"L2 = {value}", size=11, bold=chosen, color=ACCENT if chosen else TEXT)
    parent_x = MARGIN + Inches(0.1) + 2 * Inches(1.9) + Inches(0.6)
    l3_y = TOP + Inches(2.25)
    for i, value in enumerate(("10", "15", "20", "25")):
        x = MARGIN + Inches(2.0) + i * Inches(1.35)
        line(s, parent_x, l2_y + Inches(0.46), x + Inches(0.5), l3_y, color=GREY)
        node = rect(s, x, l3_y, Inches(1.0), Inches(0.42), fill=ACCENT_SOFT if i == 0 else SURFACE,
                    line=ACCENT if i == 0 else LINE)
        fill_text(node, f"L3 = {value}", size=10.5, bold=i == 0, color=ACCENT if i == 0 else TEXT)
    text(s, MARGIN + Inches(2.0), TOP + Inches(2.85), Inches(5.4), Inches(0.9), [
        "… then Light 4, then Light 5. At the bottom a complete plan is scored by the simulator.",
        "Best plan found: **0 → 40 → 10 → 40 → 15**, score 618.",
    ], size=12, color=MUTED, spacing=4)
    card(s, Inches(8.3), TOP + Inches(0.05), Inches(4.43), Inches(4.0), "How it walks the tree", [
        "Fix Light 2, then Light 3, and so on: **depth-first**.",
        "At a leaf, score the full plan and remember it if it is the best so far.",
        "Then **step back** (backtrack) and try the next value.",
        "Because nothing is skipped unsafely, the search is **complete** and the result is **optimal**.",
    ], body_size=13.5)
    notes(s, (
        "Backtracking is depth-first search over the tree of choices. Only 4 values appear per "
        "level here because forward checking (next slide) has already crossed out the others. "
        "The 'Under the hood' page draws the real search: a chart of which light is being timed at "
        "each step. Climbing means going deeper; dropping back means backtracking."
    ))

    # 22. Forward checking
    s = d.slide("Part 4 · Integration", "Step 2: forward checking crosses out bad values early",
                web="How it works › Forward checking")
    text(s, MARGIN, TOP + Inches(0.05), Inches(7.4), Inches(0.6),
         "Example: Light 2 = 40 s. A perfect wave would start Light 3 at 40 + 36 = 76 → 16 s. "
         "The rule allows 16 ± 10, so 6 to 26 s.", size=14)
    cell = Inches(0.56)
    for i in range(12):
        value = i * 5
        ok = 6 <= value <= 26
        x = MARGIN + i * (cell + Inches(0.06))
        box = rect(s, x, TOP + Inches(1.0), cell, cell, fill=GREEN_SOFT if ok else RED_SOFT,
                   line=GREEN if ok else RED, radius=0.15)
        fill_text(box, str(value), size=13, bold=ok, color=GREEN if ok else RED, margin=0)
    text(s, MARGIN, TOP + Inches(1.7), Inches(7.4), Inches(0.3),
         "Light 3's 12 values: 4 survive, 8 are crossed out before they are ever tried.", size=12, color=MUTED)
    stats = [("680", "values crossed out on the default road"),
             ("256", "plans left to score, out of 20,736 (1.2%)"),
             ("0", "dead ends: a light was never left with no value")]
    for i, (value, label) in enumerate(stats):
        x = MARGIN + i * Inches(2.5)
        rect(s, x, Inches(4.05), Inches(2.3), Inches(1.6))
        text(s, x + Inches(0.2), Inches(4.15), Inches(2), Inches(0.6), value, size=28, bold=True, color=ACCENT)
        text(s, x + Inches(0.2), Inches(4.8), Inches(1.95), Inches(0.8), label, size=12, color=MUTED)
    card(s, Inches(8.3), TOP + Inches(0.05), Inches(4.43), Inches(4.0), "Why it helps", [
        "Without it the search would build plans it already knows are illegal.",
        "With it, every branch it explores can still lead to an allowed plan.",
        "Each light keeps 4 of its 12 values, so the work drops from 12⁴ to **4⁴ = 256** plans.",
    ], body_size=13.5)
    notes(s, (
        "Forward checking looks one step ahead. As soon as one light gets a value, it removes values "
        "from the next light that would break the green-wave rule. Our constraint only links "
        "neighbouring lights, so checking the next light is enough. On the default road it crossed "
        "out 680 values: 8 values each time one of the 85 partial plans was extended. This is real "
        "pruning, and the website prints the count for your road."
    ))

    # 23. Branch and bound + verification
    s = d.slide("Part 4 · Integration", "Step 3: branch and bound, and an honest zero",
                web="Under the hood › Skipped by bound")
    card(s, MARGIN, TOP + Inches(0.05), Inches(5.85), Inches(3.0), "How branch and bound works", [
        "Keep the **best score found so far** (the incumbent).",
        "For a partial plan, estimate the lowest score it could still reach (the **bound**).",
        "If even that estimate cannot beat the incumbent, skip the whole branch.",
    ], body_size=14)
    card(s, MARGIN + Inches(6.28), TOP + Inches(0.05), Inches(5.85), Inches(3.0), "Our bound: safe but cautious", [
        "We estimate “the rest of the road adds no cost”: **h(s) = 0**.",
        "It never over-estimates, so it is **admissible**: it can never cut the true best plan.",
        "But it is so cautious it never skips anything: **0 skips** in every run.",
    ], tag="Honest result", tag_tone="warn", body_size=14)
    rect(s, MARGIN, Inches(4.95), CONTENT_W, Inches(1.5), fill=ACCENT_SOFT, line=None)
    text(s, MARGIN + Inches(0.3), Inches(5.1), CONTENT_W - Inches(0.6), Inches(1.3), [
        "The website reports the true count (0) instead of hiding it. The real speed-up comes from "
        "forward checking.",
        "A sharper bound that still never over-estimates is listed as future work.",
    ], size=14, spacing=6)
    notes(s, (
        "Branch and bound is implemented and counted, but with the bound h = 0 it never prunes. "
        "That is correct (an admissible bound keeps the answer optimal) but weak. We report the "
        "zero honestly; expect a viva question on it. Answer: h = 0 is admissible and consistent, "
        "so correctness holds, but a lower bound of 0 can never beat a real incumbent, so nothing "
        "is skipped. A better bound is future work."
    ))

    # 24. Verification
    s = d.slide("Part 4 · Integration", "Is it really the best? Double-checking the answer",
                web="Under the hood › Was the answer double-checked?")
    picture(s, "docs/screenshots/11_hood_check.png", MARGIN, TOP, h=Inches(4.4),
            crop=(0.14, 0.25, 0.14, 0.02))
    card(s, Inches(7.55), TOP, Inches(5.18), Inches(4.4), "Two kinds of proof", [
        "**Proven by the search**: the search finished, so every allowed plan was scored or "
        "safely ruled out.",
        "**Checked by brute force**: a separate, deliberately simple program scores every allowed "
        "plan one by one and must agree.",
        "Default road: brute force over **256 plans** gives the same best score, **618**.",
        "If the search hits its 30 s limit, the website says “best found in time (not proven best)”.",
    ], body_size=13.5)
    notes(s, (
        "We never just claim the answer is the best. The search itself proves it when it finishes, "
        "and an independently written brute-force verifier double-checks it whenever the number of "
        "plans is small enough (up to 250,000). In the benchmarks it agreed on 12 of 14 roads; the "
        "other 2 were too large and are reported as skipped, not as verified."
    ))

    # ---------------------------------------------------------------- Part 5
    s = d.divider("5", "Results", "What the AI achieved, on the default road and across test roads.")
    notes(s, "Part 5 shows the results with screenshots from the live website.")

    # 26. Try it result
    s = d.slide("Part 5 · Results", "The default road: 84% less waiting",
                web="Try it › headline and stats")
    picture(s, "docs/screenshots/01_try_it_form.png", MARGIN, TOP, w=Inches(6.85),
            crop=(0.41, 0.25, 0.14, 0.37))
    rows = [
        ("Waiting per car", "86.5 s", "13.5 s", "−84%"),
        ("Stops per car", "4.00", "0.97", "−76%"),
        ("Score", "3,780", "618", "−84%"),
    ]
    table(s, Inches(7.75), TOP, Inches(4.98), ["", "None", "Optimized", "Change"], rows,
          col_widths=[2.2, 1.3, 1.6, 1.3], size=13, row_h=Inches(0.55), highlight_col=2)
    text(s, Inches(7.75), TOP + Inches(2.55), Inches(4.98), Inches(2.0), [
        "Badge: **Proven best plan for this road.**",
        "Try changing the road on the website: 7 lights, heavy traffic, one way. The headline "
        "updates and the search re-runs in seconds.",
    ], size=13, color=MUTED, spacing=8)
    notes(s, (
        "This is the Try it page on the default road. An average car now waits 13.5 s instead of "
        "86.5 s and stops about once instead of four times. The green badge means the search "
        "finished and proved the plan is the best under the rules."
    ))

    # 27. Time-space
    s = d.slide("Part 5 · Results", "Seeing the difference: time-space diagrams",
                web="Try it › See the difference")
    picture(s, "docs/screenshots/03_try_it_time_space.png", MARGIN, TOP + Inches(0.4), w=Inches(6.9),
            crop=(0.14, 0.14, 0.14, 0.375))
    card(s, Inches(7.75), TOP, Inches(4.98), Inches(4.55), "How to read it", [
        "Time runs left to right; the road runs from Light 1 (bottom) to Light 5 (top).",
        "Each band is a bunch of cars. **Blue** drives up, **orange** drives down.",
        "A **flat** stretch on a red bar = cars waiting at a red light.",
        "Left: flat steps at almost every light. Right: both bands slide through.",
    ], body_size=13.5)
    notes(s, (
        "Time-space diagrams are the traffic engineer's standard picture. A straight slope means "
        "cars are moving; a flat segment means they are stopped. Without coordination both bunches "
        "stop at nearly every light. With the optimized plan both directions pass almost without "
        "stopping."
    ))

    # 28. Experiments
    s = d.slide("Part 5 · Results", "Across five test roads, the search always wins or ties",
                web="Experiments › Five test roads")
    rows = [
        ("A", "3 lights, light traffic", "762", "140", "140", "−82%", "Brute force"),
        ("B", "5 lights, moderate (default)", "3,780", "830", "618", "−84%", "Brute force"),
        ("C", "7 lights, ~3 million plans", "5,860", "1,610", "674", "−88%", "Search proof"),
        ("D", "5 lights, heavy traffic", "10,406", "2,525", "2,078", "−80%", "Brute force"),
        ("E", "5 lights, 1 s step", "3,780", "850", "605", "−84%", "Search proof"),
    ]
    table(s, MARGIN, TOP + Inches(0.05), CONTENT_W,
          ["Road", "What it tests", "None", "Green wave", "Optimized", "vs none", "Checked by"],
          rows, col_widths=[0.8, 3.4, 1.2, 1.4, 1.4, 1.1, 1.7], size=13, row_h=Inches(0.52),
          highlight_col=4)
    text(s, MARGIN, Inches(5.05), CONTENT_W, Inches(1.3), [
        "Scores = waiting + 2 × stops, lower is better. Optimized is **80–88% lower** than no "
        "coordination and up to **58% lower** than the green wave (road C).",
        "Live sweep on the website: varying the amount of traffic, the optimized plan cut waiting "
        "by **81% to 100%**.",
    ], size=13.5, color=MUTED, spacing=8)
    notes(s, (
        "These five roads were run ahead of time with the benchmark script (experiments/results). "
        "Each changes one thing from the default road. On road A the green wave is already optimal, "
        "so it ties. Roads C and E have too many plans for brute force, so their proof comes from "
        "the search running to completion with the green-wave rule on. The Experiments page also "
        "lets you run a live comparison."
    ))

    # 29. Search effort
    s = d.slide("Part 5 · Results", "How much searching it took",
                web="Under the hood › How much searching it took")
    picture(s, "docs/screenshots/12_hood_effort.png", MARGIN, TOP + Inches(0.3), w=Inches(6.9),
            crop=(0.14, 0.06, 0.14, 0.41))
    card(s, Inches(7.75), TOP, Inches(4.98), Inches(4.55), "Default road, in numbers", [
        "**20,736** possible plans; only **256** scored (1.2%).",
        "**341** values tried, **85** partial plans extended.",
        "**680** values ruled out ahead by forward checking.",
        "**0** skipped by bound, **0** dead ends.",
        "Search time: about **0.02 s**.",
        "Bigger roads: road E scored 194,481 plans in about 12 s.",
    ], body_size=13.5)
    notes(s, (
        "Every counter on the Under the hood page maps to a vocabulary word from Part 3: values "
        "tried = assignments attempted, branches explored = nodes expanded, ruled out ahead = "
        "forward-checking eliminations, skipped by bound = branch-and-bound prunes."
    ))

    # ---------------------------------------------------------------- Part 6
    s = d.divider("6", "Limits and recap", "What the model leaves out, and the whole project in one minute.")
    notes(s, "Part 6 closes with honest limitations and a summary you can say out loud.")

    # 31. Limitations
    s = d.slide("Part 6 · Limits", "What the model simplifies (said honestly)")
    lims = [
        ("No queues", "Cars never pile up behind each other; heavy traffic is gentler than in reality."),
        ("Constant speed", "Every car drives exactly at the speed limit, no braking or accelerating."),
        ("One road, one phase", "No turning cars, pedestrians or side streets."),
        ("Synthetic traffic", "Cars are generated, not measured from a real road."),
        ("Weak bound", "h = 0 never prunes; a sharper admissible bound is future work."),
        ("Big roads", "7+ lights need the green-wave rule to stay fast; proof is within that rule."),
    ]
    pw = (CONTENT_W - 2 * Inches(0.25)) / 3
    for i, (name, body) in enumerate(lims):
        x = MARGIN + (i % 3) * (pw + Inches(0.25))
        y = TOP + Inches(0.05) + (i // 3) * Inches(1.9)
        card(s, x, y, pw, Inches(1.7), name, body, body_size=13)
    text(s, MARGIN, Inches(5.85), CONTENT_W, Inches(0.6),
         "Future work: a sharper bound · queues in the simulator · local search for very large "
         "roads · turning phases · testing on a real road layout.", size=13, color=MUTED)
    notes(s, (
        "Say these before you are asked. The numbers are simulated under simplifications, so they "
        "compare plans fairly but are not field predictions. The project is a demonstration of "
        "classical AI search, not a traffic-engineering tool."
    ))

    # 32. Recap
    s = d.slide("Part 6 · Recap", "The whole project in one minute")
    recap = [
        ("Problem", "Uncoordinated traffic lights make cars stop at almost every light: 86.5 s "
                    "waiting and 4 stops per car on our default road."),
        ("AI technique", "Model the offsets as a constraint satisfaction problem and solve it with "
                         "backtracking, forward checking and branch and bound."),
        ("Integration", "One deterministic simulator scores every plan; a brute-force verifier "
                        "double-checks the answer; a four-page website explains it all."),
        ("Result", "13.5 s waiting and 0.97 stops per car (−84%); 80–88% lower scores on every "
                   "test road; optimality proven or brute-force checked."),
    ]
    for i, (name, body) in enumerate(recap):
        y = TOP + Inches(0.05) + i * Inches(1.08)
        rect(s, MARGIN, y, CONTENT_W, Inches(0.95))
        text(s, MARGIN + Inches(0.3), y, Inches(2.2), Inches(0.95), name, size=17, bold=True,
             color=ACCENT, anchor=MSO_ANCHOR.MIDDLE)
        text(s, MARGIN + Inches(2.6), y, CONTENT_W - Inches(2.9), Inches(0.95), body, size=14,
             anchor=MSO_ANCHOR.MIDDLE)
    notes(s, (
        "If you only remember one slide, remember this one. Problem: wasted waiting at "
        "uncoordinated lights. Technique: a CSP solved by backtracking with forward checking and "
        "branch and bound. Integration: a shared simulator, an independent verifier and the "
        "website. Result: 84% less waiting on the default road, proven optimal."
    ))

    # 33. Viva prep
    s = d.slide("Part 6 · Recap", "Questions you will probably be asked")
    qa = [
        ("Where is the AI?", "The CSP search that picks the offsets: backtracking + forward "
                             "checking + branch and bound."),
        ("Why not try every plan?", "It grows ×12 per light (3 million at 7 lights). Pruning keeps "
                                    "it to 256 plans on the default road."),
        ("How do you know it is the best?", "The search is complete, and brute force agrees "
                                            "wherever the space is small enough."),
        ("Why does branch and bound prune 0?", "Our bound h = 0 is admissible but weak; we report "
                                               "the true count."),
        ("Why not machine learning?", "The rules are known exactly and there is no data; search "
                                      "gives a proven-best answer."),
        ("Is it realistic?", "It is a simplified simulator: fair for comparing plans, not a field "
                             "prediction."),
    ]
    pw = (CONTENT_W - Inches(0.25)) / 2
    for i, (q, a) in enumerate(qa):
        x = MARGIN + (i % 2) * (pw + Inches(0.25))
        y = TOP + Inches(0.05) + (i // 2) * Inches(1.45)
        card(s, x, y, pw, Inches(1.3), q, a, title_size=15, body_size=13)
    text(s, MARGIN, Inches(6.25), CONTENT_W, Inches(0.3),
         "More answers: docs/viva_questions.md (42 questions).", size=12, color=MUTED)
    notes(s, "Short answers to the most likely viva questions. The full list is in docs/viva_questions.md.")

    return d.prs


def write_notes(deck: Presentation, path: Path) -> None:
    """Export every slide's title and speaker notes as a markdown read-along script."""
    lines = [
        f"# Speaker notes — read-along deck ({len(deck.slides._sldIdLst)} slides)",
        "",
        "Generated by `tools/build_slides.py` from the notes embedded in",
        "`deliverables/final_slides.pptx`. Read each slide with the dashboard open",
        "on the page named in the slide's \"On the website\" tag.",
        "",
    ]
    for number, slide in enumerate(deck.slides, start=1):
        title = next(shape.text_frame.text for shape in slide.shapes if shape.name == "Title")
        lines += [f"## Slide {number} — {title}", "",
                  slide.notes_slide.notes_text_frame.text, ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """Build and save the PPTX and the matching speaker notes."""
    deck = build()
    output = OUT / "final_slides.pptx"
    deck.save(output)
    write_notes(deck, OUT / "speaker_notes.md")
    print(f"saved {output}, {len(deck.slides._sldIdLst)} slides")


if __name__ == "__main__":
    main()
