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
    pill(s, Inches(8.8), Inches(5.0), "On the website  ›  Page › Section", size=10.5)
    text(s, Inches(8.8), Inches(5.45), Inches(3.9), Inches(0.9),
         "Read with the dashboard open: this tag on each slide names the page and section that "
         "shows the same idea live.", size=12, color=MUTED)
    notes(s, (
        "This deck is meant to be read next to the website. Every slide has a blue tag in the top "
        "right that tells you which page and section of the dashboard shows the same idea. Open "
        "the dashboard (python -m streamlit run app.py) and keep it beside the slides."
    ))

    # 5. Why it happens
    s = d.slide("The problem", "Why it happens: every light turns green together",
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
    text(s, MARGIN, Inches(5.3), Inches(7.3), Inches(0.3),
         "Green bar = light is green, red bar = light is red. Every row is the same.",
         size=12, color=MUTED)
    text(s, MARGIN, Inches(5.75), Inches(7.3), Inches(0.6),
         "Result on the default road (5 lights, 400 m apart, 40 km/h, 40 cars): an average car "
         "waits **86.5 s** and stops **4.0 times**.", size=14, color=RED)
    notes(s, (
        "This is the core of the problem. The timing bars show 3 minutes of five lights that all "
        "start green at the same moment. Driving between lights takes 36 seconds, but the green "
        "only lasts 30 seconds, so a car always arrives just after its light turned red. The "
        "'How it works' page opens with exactly this explanation, using your road's numbers."
    ))

    # 6. The fix
    s = d.slide("The problem", "The fix: delay each light's green (a green wave)",
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
        "directions and the plan has to suit both; the next slide explains why that is hard."
    ))

    # 7. Why hard
    s = d.slide("The problem", "Why we need AI: too many plans to check by hand",
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

    # Classical AI, the agent and its environment
    s = d.slide("Classical AI", "What kind of AI this is",
                lede="Foundations of AI is about agents that solve exactly described problems by "
                     "searching, not about training neural networks.")
    card(s, MARGIN, TOP + Inches(0.05), Inches(5.85), Inches(2.3), "Classical AI  (this project)", [
        "Rules and goal are written down exactly; a search **proves** which plan is best.",
        "No training data, no guessing: the same road always gives the same plan.",
    ], tag="What we use", body_size=13, border=ACCENT)
    card(s, MARGIN + Inches(6.28), TOP + Inches(0.05), Inches(5.85), Inches(2.3),
         "Machine learning  (not used)", [
             "Learns patterns from lots of example data and gives a good guess.",
             "Needs data we do not have, and usually no guarantee of the best answer.",
         ], tag="Not used", tag_tone="grey", body_size=13)
    peas = [
        ("P", "Performance", "The **score**: waiting + 2 × stops, lower is better."),
        ("E", "Environment", "A simulated road with N lights and fixed cars both ways."),
        ("A", "Actuators", "Choosing the **offset** of each light (the timing plan)."),
        ("S", "Sensors", "The simulator's report: each car's waiting and stops."),
    ]
    text(s, MARGIN, TOP + Inches(2.5), CONTENT_W, Inches(0.3),
         "Our project as an AI agent (PEAS, from the textbook)", size=14, bold=True)
    pw = (CONTENT_W - 3 * Inches(0.25)) / 4
    for i, (letter, name, body) in enumerate(peas):
        x = MARGIN + i * (pw + Inches(0.25))
        y = TOP + Inches(2.9)
        rect(s, x, y, pw, Inches(1.35))
        text(s, x + Inches(0.2), y + Inches(0.12), Inches(0.5), Inches(0.6), letter, size=28,
             bold=True, color=ACCENT)
        text(s, x + Inches(0.75), y + Inches(0.22), pw - Inches(0.9), Inches(0.35), name, size=14,
             bold=True)
        text(s, x + Inches(0.2), y + Inches(0.72), pw - Inches(0.4), Inches(0.7), body, size=12,
             color=MUTED)
    text(s, MARGIN, Inches(6.2), CONTENT_W, Inches(0.4),
         "Environment: **fully observable, deterministic, static, discrete, single agent, known**. "
         "That is why exact search can compute every score and prove the best plan.",
         size=12.5, color=MUTED)
    notes(s, (
        "People hear 'AI' and think of ChatGPT, which is machine learning. Foundations of AI starts "
        "with problems you can describe exactly, solved by searching through possibilities in a smart "
        "way. Our project is entirely classical AI. PEAS is the textbook's way to describe an agent: "
        "its goal is the lowest score, its world is the simulated road, its only action is choosing "
        "offsets, and what it 'sees' is the simulator's result. It plans offline; it does not control "
        "real lights. The six environment words explain why exact search works here: real traffic "
        "is random and partly hidden, our simulated road is not."
    ))

    # Vocabulary
    s = d.slide("Vocabulary", "FAI words, and what the website calls them",
                web="How it works › Words used on this site")
    rows = [
        ("CSP", "Problem given as unknowns, their allowed values and rules", "“a puzzle with rules”"),
        ("Variable", "One unknown: the offset of Light 2, 3, 4 or 5", "Offset (delay)"),
        ("Domain", "Allowed values: {0, 5, 10, …, 55} s", "Timing step, 12 choices"),
        ("Constraint", "Rule to obey: within ±10 s of a perfect green wave", "Green-wave rule"),
        ("Objective", "Number to minimise: J = waiting + 2 × stops", "Score"),
        ("Backtracking", "Depth-first search that steps back to try the next value", "Backtracking"),
        ("Forward checking", "Cross out the next light's values that break the rule", "Ruled out ahead"),
        ("Branch and bound", "Skip branches that cannot beat the best plan so far", "Skipped by bound"),
        ("Admissible bound", "Estimate that never over-estimates, so skipping is safe", "Safe but cautious"),
        ("Complete / optimal", "Never misses a solution / returns the best one", "Best possible"),
        ("Greedy", "Decide once with a rule of thumb, never reconsider", "Simple green wave"),
    ]
    table(s, MARGIN, TOP - Inches(0.1), CONTENT_W, ["FAI term", "Meaning in this project", "Website word"],
          rows, col_widths=[2.4, 6.4, 2.6], size=12.5, row_h=Inches(0.42), highlight_col=2)
    notes(s, (
        "This one table is the vocabulary for the whole project. A CSP, constraint satisfaction "
        "problem, has variables (the offsets), domains (12 allowed values each) and constraints "
        "(the green-wave rule); we add an objective, the score, so we want the best allowed plan. "
        "Backtracking walks the tree of choices, forward checking and branch and bound prune it. "
        "The right column is the plain word the website uses, so you can find each idea there."
    ))

    # 17. Pipeline
    s = d.slide("How it works", "The pipeline: what happens when you press the button",
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
    s = d.slide("How it works", "Our problem written as a CSP",
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
    text(s, MARGIN, Inches(5.6), CONTENT_W, Inches(0.8), [
        "W = total seconds all cars wait at red lights, S = total stops. A stop costs 2 extra "
        "seconds because braking and pulling away waste time and fuel.",
        "Worked out: no coordination 3,460 + 2 × 160 = **3,780**;  optimized 540 + 2 × 39 = **618**.",
    ], size=12.5, color=MUTED, spacing=4)
    notes(s, (
        "This is the formal CSP. Four variables, twelve values each, one rule per pair of "
        "neighbouring lights, and an objective. The rule says each light's offset should be close "
        "(within 10 s) to the previous light's offset plus the driving time, which is what a green "
        "wave would be. It keeps plans sensible and the search small: 256 allowed plans instead of "
        "20,736."
    ))

    # 20. Baselines
    s = d.slide("How it works", "Strategies 1 and 2: the comparisons",
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
    s = d.slide("How it works", "Strategy 3, step 1: backtracking search",
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
    s = d.slide("How it works", "Step 2: forward checking crosses out bad values early",
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

    # Branch and bound + verification
    s = d.slide("How it works", "Step 3: branch and bound, and checking the answer",
                web="Under the hood › Was the answer double-checked?")
    card(s, MARGIN, TOP + Inches(0.05), Inches(5.85), Inches(3.3), "Branch and bound: an honest zero", [
        "Keep the **best score so far**; skip a branch if an optimistic estimate (the **bound**) "
        "says it cannot beat it.",
        "Our estimate is “the rest of the road adds no cost”: **h = 0**. It never over-estimates, "
        "so it is **admissible** and safe.",
        "But it is so cautious it never skips anything: **0 skips**. The website shows the true 0.",
    ], tag="Honest result", tag_tone="warn", body_size=13.5)
    card(s, MARGIN + Inches(6.28), TOP + Inches(0.05), Inches(5.85), Inches(3.3), "Is it really the best?", [
        "**Proven by the search**: it finished, so every allowed plan was scored or safely ruled out.",
        "**Checked by brute force**: a separate, simple program scores every allowed plan and must agree.",
        "If the 30 s limit is hit, the website says “best found in time (not proven best)”.",
    ], tag="Two kinds of proof", tag_tone="green", body_size=13.5)
    rect(s, MARGIN, Inches(5.3), CONTENT_W, Inches(1.1), fill=GREEN_SOFT, line=None)
    text(s, MARGIN + Inches(0.3), Inches(5.3), CONTENT_W - Inches(0.6), Inches(1.1),
         "**Yes, confirmed.** Brute force over all 256 allowed plans gives the same best score, 618. "
         "In the benchmarks it agreed on 12 of 14 roads; the 2 too large to check are reported as skipped.",
         size=14, anchor=MSO_ANCHOR.MIDDLE)
    notes(s, (
        "Branch and bound is implemented and counted, but with the bound h = 0 it never prunes. That "
        "is correct (an admissible bound keeps the answer optimal) but weak, and we report the zero "
        "honestly; a sharper bound is future work. We never just claim the answer is the best: the "
        "finished search proves it, and an independently written brute-force verifier double-checks "
        "it whenever there are at most 250,000 plans."
    ))

    # Default road result
    s = d.slide("Results", "The default road: 84% less waiting",
                web="Try it › See the difference")
    picture(s, "docs/screenshots/03_try_it_time_space.png", MARGIN, TOP + Inches(0.05), w=Inches(6.9),
            crop=(0.14, 0.14, 0.14, 0.375))
    text(s, MARGIN, TOP + Inches(3.25), Inches(6.9), Inches(1.2), [
        "Each band is a bunch of cars (**blue** up the road, **orange** down). A **flat** stretch on "
        "a red bar means cars waiting. Left, no coordination: flat steps at almost every light. "
        "Right, optimized: both bands slide through.",
    ], size=12, color=MUTED)
    rows = [
        ("Waiting per car", "86.5 s", "13.5 s", "−84%"),
        ("Stops per car", "4.00", "0.97", "−76%"),
        ("Score", "3,780", "618", "−84%"),
    ]
    table(s, Inches(7.75), TOP + Inches(0.05), Inches(4.98), ["", "None", "Optimized", "Change"], rows,
          col_widths=[2.2, 1.3, 1.6, 1.3], size=13, row_h=Inches(0.55), highlight_col=2)
    text(s, Inches(7.75), TOP + Inches(2.5), Inches(4.98), Inches(2.0), [
        "Plan: **0, +40, +10, +40, +15 s**. Badge: **Proven best plan for this road.**",
        "The search scored 256 of 20,736 plans in about 0.02 s.",
        "Try it live: 7 lights, heavy traffic, one way, and press Find the best timings.",
    ], size=13, color=MUTED, spacing=8)
    notes(s, (
        "This is the Try it page on the default road. An average car now waits 13.5 s instead of "
        "86.5 s and stops about once instead of four times. The time-space diagrams are the traffic "
        "engineer's standard picture: a slope means moving, a flat segment means stopped. The green "
        "badge means the search finished and proved the plan is the best under the rules."
    ))

    # 28. Experiments
    s = d.slide("Results", "Across five test roads, the search always wins or ties",
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

    # Limits and recap
    s = d.slide("Wrap-up", "Limits, and the whole project in one minute")
    card(s, MARGIN, TOP + Inches(0.05), Inches(4.4), Inches(4.45), "What the model simplifies", [
        "No queues: cars never pile up.",
        "Constant speed, no braking.",
        "One road: no turns or pedestrians.",
        "Generated traffic, not measured.",
        "Weak bound: h = 0 never prunes.",
        "Future: sharper bound, queues, real road layout.",
    ], tag="Said honestly", tag_tone="grey", body_size=13)
    recap = [
        ("Problem", "Uncoordinated lights: 86.5 s waiting and 4 stops per car on the default road."),
        ("AI technique", "Offsets as a CSP, solved by backtracking, forward checking and branch and bound."),
        ("Integration", "One simulator scores every plan; brute force double-checks; the website explains it."),
        ("Result", "13.5 s and 0.97 stops per car (−84%); 80–88% lower on every test road, proven best."),
    ]
    rx = MARGIN + Inches(4.65)
    rw = CONTENT_W - Inches(4.65)
    for i, (name, body) in enumerate(recap):
        y = TOP + Inches(0.05) + i * Inches(1.14)
        rect(s, rx, y, rw, Inches(1.0))
        text(s, rx + Inches(0.25), y, Inches(1.7), Inches(1.0), name, size=15, bold=True,
             color=ACCENT, anchor=MSO_ANCHOR.MIDDLE)
        text(s, rx + Inches(2.0), y, rw - Inches(2.2), Inches(1.0), body, size=13,
             anchor=MSO_ANCHOR.MIDDLE)
    notes(s, (
        "Say the limitations before you are asked: the numbers are simulated under simplifications, "
        "so they compare plans fairly but are not field predictions. Then the one-minute summary. "
        "Likely viva questions: Where is the AI? (the CSP search). Why not try every plan? (it grows "
        "x12 per light; pruning keeps it to 256). How do you know it is the best? (complete search, "
        "brute force agrees). Why does branch and bound prune 0? (h = 0 is admissible but weak). Why "
        "not machine learning? (rules are known, no data). More in docs/viva_questions.md."
    ))

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
