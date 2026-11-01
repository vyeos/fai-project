"""Dashboard design system: global CSS and small HTML builders for the pages.

One set of tokens (from :mod:`traffic_coordination.visualization`) drives the
Streamlit theme, this stylesheet and every Plotly chart. Each builder returns a
string that a page renders with ``st.html``. Plain-text arguments are escaped;
arguments named ``*_html`` are trusted markup written by the app itself.

Components, smallest first:

- ``badge``: a short status word with a coloured dot
- ``page_header`` / ``section``: the only two heading levels on a page
- ``summary``: the one sentence that answers "so what?" for a result
- ``stat_grid``: a row of numbers, each with a label and a before-value
- ``strategy_cards``: the three timing strategies side by side
- ``plan_table``: when each light turns green, in words
- ``terms`` / ``steps``: glossary entries and numbered explanations
- ``callout`` / ``empty_state``: inline notices
- ``signal_row``: animated traffic lights running a timing plan
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
from dataclasses import dataclass
from html import escape

from .visualization import (
    ALGORITHM_COLORS,
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_FAINT,
    COLOR_GREEN,
    COLOR_LINE,
    COLOR_MUTED,
    COLOR_RED,
    COLOR_SUNKEN,
    COLOR_SURFACE,
    COLOR_TEXT,
)

__all__ = [
    "GLOBAL_CSS",
    "Stat",
    "StrategyCard",
    "badge",
    "callout",
    "empty_state",
    "legend",
    "page_header",
    "plan_table",
    "section",
    "signal_row",
    "signal_row_svg",
    "stat_grid",
    "steps",
    "strategy_cards",
    "summary",
    "terms",
]

# Real seconds of signal time per animated second in the signal row.
TIME_SCALE = 10.0

GLOBAL_CSS = f"""
<style>
:root {{
  --bg: {COLOR_BG};
  --surface: {COLOR_SURFACE};
  --sunken: {COLOR_SUNKEN};
  --line: {COLOR_LINE};
  --text: {COLOR_TEXT};
  --muted: {COLOR_MUTED};
  --faint: {COLOR_FAINT};
  --accent: {COLOR_ACCENT};
  --accent-soft: rgba(36, 87, 214, 0.08);
  --go: {COLOR_GREEN};
  --go-soft: rgba(30, 154, 90, 0.09);
  --stop: {COLOR_RED};
  --stop-soft: rgba(214, 67, 59, 0.08);
  --warn: #b7791f;
  --warn-soft: rgba(227, 162, 26, 0.12);
  --sans: 'IBM Plex Sans', ui-sans-serif, system-ui, sans-serif;
  --mono: 'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
  --radius: 10px;
  --ease: cubic-bezier(0.2, 0.8, 0.2, 1);
}}

/* ---- canvas ---------------------------------------------------------- */
html, body, [data-testid="stAppViewContainer"] {{ background: var(--bg); }}
[data-testid="stHeader"] {{ background: var(--bg); border-bottom: 1px solid var(--line); }}
[data-testid="stMainBlockContainer"] {{ max-width: 1180px; padding-top: 4.5rem; padding-bottom: 4rem; }}
[data-testid="stMain"] p, [data-testid="stMain"] li {{ color: var(--muted); }}
[data-testid="stMain"] strong {{ color: var(--text); font-weight: 600; }}
code, [data-testid="stMain"] code {{
  font-family: var(--mono); font-size: 0.86em; color: var(--text);
  background: var(--sunken); border: 0; padding: 0.08em 0.35em; border-radius: 4px;
}}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color: var(--faint) !important; font-size: 0.84rem; }}
hr {{ border-color: var(--line) !important; }}

/* ---- widgets --------------------------------------------------------- */
[data-testid="stForm"] {{
  background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 1.25rem 1.25rem 1.1rem;
}}
[data-testid="stWidgetLabel"] p {{ color: var(--text) !important; font-weight: 500; font-size: 0.9rem; }}
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primaryFormSubmit"], [data-testid="stBaseButton-secondaryFormSubmit"],
[data-testid="stDownloadButton"] button {{
  border-radius: 8px; font-weight: 500; min-height: 2.6rem;
  transition: background-color 0.2s var(--ease), border-color 0.2s var(--ease);
}}
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {{
  background: var(--accent); border-color: var(--accent);
}}
[data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover {{
  background: #1c48b8; border-color: #1c48b8;
}}
[data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primaryFormSubmit"] p {{ color: #fff; }}
[data-testid="stExpander"] details {{ border: 1px solid var(--line); border-radius: 8px; background: var(--surface); }}
[data-testid="stDataFrame"] {{ border: 1px solid var(--line); border-radius: 8px; }}
[data-testid="stPlotlyChart"] {{
  background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 0.6rem 0.75rem 0.25rem;
}}

/* ---- headings -------------------------------------------------------- */
.ui-page {{ margin: 0 0 1.75rem; max-width: 72ch; }}
.ui-page h1 {{
  font-family: var(--sans); font-size: clamp(1.75rem, 3.2vw, 2.3rem); font-weight: 600;
  letter-spacing: -0.02em; line-height: 1.15; color: var(--text); margin: 0 0 0.6rem; padding: 0;
}}
.ui-page p {{ font-size: 1.04rem; line-height: 1.6; color: var(--muted); margin: 0; }}
.ui-section {{ margin: 2.4rem 0 0.9rem; max-width: 76ch; }}
.ui-section.first {{ margin-top: 0; }}
.ui-section h2 {{
  font-family: var(--sans); font-size: 1.25rem; font-weight: 600; letter-spacing: -0.01em;
  color: var(--text); margin: 0 0 0.35rem; padding: 0;
}}
.ui-section p {{ margin: 0; color: var(--muted); line-height: 1.6; font-size: 0.95rem; }}
.ui-section p + p {{ margin-top: 0.5rem; }}

/* ---- badge ----------------------------------------------------------- */
.ui-badge {{
  display: inline-flex; align-items: center; gap: 0.4rem; white-space: nowrap;
  font-size: 0.78rem; font-weight: 500; color: var(--muted);
  padding: 0.15rem 0.55rem; border-radius: 999px; background: var(--sunken);
}}
.ui-badge i {{ width: 6px; height: 6px; border-radius: 50%; background: var(--faint); }}
.ui-badge.ok {{ background: var(--go-soft); color: #17784a; }}
.ui-badge.ok i {{ background: var(--go); }}
.ui-badge.warn {{ background: var(--warn-soft); color: #8a5a12; }}
.ui-badge.warn i {{ background: var(--warn); }}
.ui-badge.bad {{ background: var(--stop-soft); color: #a8322b; }}
.ui-badge.bad i {{ background: var(--stop); }}

/* ---- summary --------------------------------------------------------- */
.ui-summary {{
  background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 1.25rem 1.4rem;
}}
.ui-summary h3 {{
  font-family: var(--sans); font-size: 1.2rem; font-weight: 500; line-height: 1.45;
  color: var(--text); margin: 0; padding: 0; letter-spacing: -0.005em;
}}
.ui-summary h3 b {{ font-weight: 600; color: var(--accent); }}
.ui-summary p {{ margin: 0.6rem 0 0; color: var(--muted); font-size: 0.9rem; line-height: 1.55; }}
.ui-summary .ui-badge {{ margin-top: 0.85rem; }}

/* ---- stats ----------------------------------------------------------- */
.ui-stats {{ padding: 0 !important; display: grid; grid-template-columns: repeat(auto-fit, minmax(10.5rem, 1fr)); gap: 0.75rem; margin-top: 0.75rem; }}
.ui-stat {{ background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 0.95rem 1.1rem; }}
.ui-stat dt {{ font-size: 0.84rem; color: var(--muted); margin: 0 0 0.35rem; }}
.ui-stat dd {{ margin: 0; }}
.ui-stat .v {{ font-size: 1.7rem; font-weight: 600; color: var(--text); letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }}
.ui-stat .v small {{ font-size: 0.55em; font-weight: 500; color: var(--faint); margin-left: 0.25rem; letter-spacing: 0; }}
.ui-stat .was {{ display: block; margin-top: 0.2rem; font-size: 0.82rem; color: var(--faint); font-variant-numeric: tabular-nums; }}
.ui-stat .was b {{ color: #17784a; font-weight: 600; }}

/* ---- strategy cards -------------------------------------------------- */
.ui-cards {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.75rem; }}
.ui-card {{
  background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 1.1rem 1.2rem; display: flex; flex-direction: column; gap: 0.7rem;
}}
.ui-card.best {{ border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent) inset; }}
.ui-card header {{ display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; }}
.ui-card h4 {{ display: flex; align-items: center; gap: 0.5rem; margin: 0; padding: 0; font-family: var(--sans); font-size: 1rem; font-weight: 600; color: var(--text); }}
.ui-card h4 i {{ width: 10px; height: 10px; border-radius: 3px; flex: none; }}
.ui-card > p {{ margin: 0; font-size: 0.88rem; line-height: 1.5; color: var(--muted); }}
.ui-card dl {{ margin: auto 0 0; display: grid; gap: 0.35rem; padding-top: 0.7rem; border-top: 1px solid var(--line); }}
.ui-card dl div {{ display: flex; justify-content: space-between; gap: 1rem; }}
.ui-card dt {{ font-size: 0.86rem; color: var(--muted); }}
.ui-card dd {{ margin: 0; font-size: 0.9rem; font-weight: 600; color: var(--text); font-variant-numeric: tabular-nums; }}
.ui-card .bar {{ height: 6px; border-radius: 3px; background: var(--sunken); overflow: hidden; }}
.ui-card .bar i {{ display: block; height: 100%; border-radius: 3px; transform-origin: left; animation: ui-grow 0.9s var(--ease) both; }}

/* ---- plan table ------------------------------------------------------ */
.ui-plan {{ width: 100%; border-collapse: collapse; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }}
.ui-plan th {{ text-align: left; font-size: 0.82rem; font-weight: 500; color: var(--muted); background: var(--sunken); padding: 0.6rem 1rem; }}
.ui-plan td {{ padding: 0.7rem 1rem; border-top: 1px solid var(--line); font-size: 0.92rem; color: var(--muted); vertical-align: top; }}
.ui-plan td:first-child {{ color: var(--text); font-weight: 500; white-space: nowrap; }}
.ui-plan td.n {{ color: var(--text); font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap; }}

/* ---- terms + steps --------------------------------------------------- */
.ui-terms {{ padding: 0 !important; display: grid; grid-template-columns: repeat(auto-fit, minmax(17rem, 1fr)); gap: 0.75rem; margin: 0; }}
.ui-terms div {{ background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 0.9rem 1.05rem; }}
.ui-terms dt {{ display: flex; justify-content: space-between; align-items: baseline; gap: 0.75rem; font-weight: 600; color: var(--text); font-size: 0.95rem; margin-bottom: 0.3rem; }}
.ui-terms dt span {{ font-weight: 600; color: var(--accent); font-variant-numeric: tabular-nums; white-space: nowrap; }}
.ui-terms dd {{ margin: 0; color: var(--muted); font-size: 0.88rem; line-height: 1.55; }}
.ui-steps {{ list-style: none; margin: 0; padding: 0 !important; display: grid; gap: 0.6rem; counter-reset: step; max-width: 78ch; }}
.ui-steps li {{ display: grid; grid-template-columns: 1.9rem 1fr; gap: 0.85rem; counter-increment: step; }}
.ui-steps li::before {{
  content: counter(step); width: 1.9rem; height: 1.9rem; border-radius: 50%;
  display: grid; place-items: center; font-size: 0.85rem; font-weight: 600;
  color: var(--accent); background: var(--accent-soft);
}}
.ui-steps .t {{ display: block; color: var(--text); font-weight: 600; font-size: 0.97rem; margin: 0.25rem 0 0.15rem; }}
.ui-steps p {{ margin: 0; color: var(--muted); font-size: 0.92rem; line-height: 1.6; }}

/* ---- callout + empty ------------------------------------------------- */
.ui-callout {{ border-radius: var(--radius); padding: 0.85rem 1.05rem; background: var(--sunken); }}
.ui-callout p {{ margin: 0; color: var(--text); font-size: 0.92rem; line-height: 1.55; }}
.ui-callout.ok {{ background: var(--go-soft); }}
.ui-callout.warn {{ background: var(--warn-soft); }}
.ui-callout.bad {{ background: var(--stop-soft); }}
.ui-callout.info {{ background: var(--accent-soft); }}
.ui-empty {{ border: 1px dashed var(--line); border-radius: var(--radius); padding: 1.5rem; text-align: center; background: var(--surface); }}
.ui-empty h4 {{ margin: 0 0 0.3rem; padding: 0; font-family: var(--sans); font-size: 1rem; font-weight: 600; color: var(--text); }}
.ui-empty p {{ margin: 0 auto; max-width: 52ch; color: var(--muted); font-size: 0.9rem; line-height: 1.55; }}

/* ---- legend + signal row --------------------------------------------- */
.ui-legend {{ display: flex; flex-wrap: wrap; gap: 0.4rem 1.25rem; margin: 0.25rem 0 0.6rem; }}
.ui-legend span {{ display: inline-flex; align-items: center; gap: 0.45rem; font-size: 0.85rem; color: var(--muted); }}
.ui-legend i {{ display: inline-block; width: 18px; height: 4px; border-radius: 2px; }}
.ui-legend i.bar {{ height: 7px; }}
.ui-signals {{ background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 1rem 1.1rem 0.8rem; }}
.ui-signals img {{ width: 100%; height: auto; display: block; }}
.ui-signals .labels {{ display: grid; text-align: center; margin-top: 0.4rem; }}
.ui-signals .labels b {{ display: block; font-size: 0.82rem; font-weight: 600; color: var(--text); }}
.ui-signals .labels span {{ font-size: 0.78rem; color: var(--muted); font-variant-numeric: tabular-nums; }}
.ui-signals p {{ margin: 0.7rem 0 0; font-size: 0.82rem; color: var(--faint); text-align: center; }}

@keyframes ui-grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}

@media (max-width: 860px) {{
  .ui-cards {{ grid-template-columns: 1fr; }}
}}
@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"] {{ padding-left: 1rem; padding-right: 1rem; padding-top: 4rem; }}
  .ui-plan th, .ui-plan td {{ padding-left: 0.6rem; padding-right: 0.6rem; }}
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation: none !important; transition: none !important; }}
}}
</style>
"""


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def badge(text: str, tone: str = "neutral") -> str:
    """Short status word with a dot; ``tone`` is ok, warn, bad or neutral."""
    return f'<span class="ui-badge {_e(tone)}"><i></i>{_e(text)}</span>'


def page_header(title: str, lede_html: str) -> str:
    """Page title plus one paragraph saying what the page is for."""
    return f'<header class="ui-page"><h1>{_e(title)}</h1><p>{lede_html}</p></header>'


def section(title: str, *paragraphs_html: str, first: bool = False) -> str:
    """Section heading with zero or more short explanatory paragraphs."""
    body = "".join(f"<p>{p}</p>" for p in paragraphs_html)
    cls = "ui-section first" if first else "ui-section"
    return f'<div class="{cls}"><h2>{_e(title)}</h2>{body}</div>'


def summary(headline_html: str, note_html: str = "", badge_html: str = "") -> str:
    """Give the one-sentence answer for a result, with an optional note and badge."""
    note = f"<p>{note_html}</p>" if note_html else ""
    return f'<div class="ui-summary"><h3>{headline_html}</h3>{note}{badge_html}</div>'


@dataclass(frozen=True)
class Stat:
    """One figure in a ``stat_grid``: label, value, unit and optional baseline."""

    label: str
    value: str
    unit: str = ""
    was: str = ""
    change: str = ""


def stat_grid(stats: Sequence[Stat]) -> str:
    """Row of stat cards; ``was`` and ``change`` render as 'was X · -85%'."""
    cells = []
    for s in stats:
        unit = f"<small>{_e(s.unit)}</small>" if s.unit else ""
        was = ""
        if s.was:
            change = f" &middot; <b>{_e(s.change)}</b>" if s.change else ""
            was = f'<span class="was">was {_e(s.was)}{change}</span>'
        cells.append(
            f'<div class="ui-stat"><dt>{_e(s.label)}</dt>'
            f'<dd><span class="v">{_e(s.value)}{unit}</span>{was}</dd></div>'
        )
    return f'<dl class="ui-stats">{"".join(cells)}</dl>'


@dataclass(frozen=True)
class StrategyCard:
    """One strategy's card: plain name, what it does, and its scores."""

    algorithm: str
    name: str
    description: str
    status: str
    tone: str
    wait_per_car: float
    stops_per_car: float
    score: float


def strategy_cards(cards: Sequence[StrategyCard]) -> str:
    """Three cards side by side; the lowest score is outlined as the best."""
    if not cards:
        return ""
    worst = max(c.score for c in cards) or 1.0
    best = min(c.score for c in cards)
    out = []
    for c in cards:
        color = ALGORITHM_COLORS.get(c.algorithm, COLOR_MUTED)
        width = max(c.score / worst * 100.0, 0.8)
        cls = "ui-card best" if c.score == best else "ui-card"
        out.append(
            f'<article class="{cls}"><header>'
            f'<h4><i style="background:{color}"></i>{_e(c.name)}</h4>{badge(c.status, c.tone)}'
            f"</header><p>{_e(c.description)}</p><dl>"
            f"<div><dt>Waiting per car</dt><dd>{c.wait_per_car:,.1f} s</dd></div>"
            f"<div><dt>Stops per car</dt><dd>{c.stops_per_car:,.2f}</dd></div>"
            f"<div><dt>Score (lower is better)</dt><dd>{c.score:,.0f}</dd></div>"
            f'</dl><div class="bar"><i style="width:{width:.2f}%;background:{color}"></i></div>'
            "</article>"
        )
    return f'<div class="ui-cards">{"".join(out)}</div>'


def plan_table(headers: Sequence[str], rows: Sequence[Sequence[str]], numeric: int = 1) -> str:
    """Build a simple table; column ``numeric`` is drawn as a bold figure."""
    head = "".join(f"<th>{_e(h)}</th>" for h in headers)
    body = "".join(
        "<tr>"
        + "".join(
            f'<td class="n">{_e(cell)}</td>' if i == numeric else f"<td>{_e(cell)}</td>"
            for i, cell in enumerate(row)
        )
        + "</tr>"
        for row in rows
    )
    return f'<table class="ui-plan"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def terms(items: Sequence[tuple[str, str, str]]) -> str:
    """Glossary cards of ``(term, value, explanation_html)``; value may be ''."""
    cells = "".join(
        f"<div><dt>{_e(term)}{f'<span>{_e(value)}</span>' if value else ''}</dt>"
        f"<dd>{explanation}</dd></div>"
        for term, value, explanation in items
    )
    return f'<dl class="ui-terms">{cells}</dl>'


def steps(items: Sequence[tuple[str, str]]) -> str:
    """Numbered list of ``(title, body_html)`` explanations."""
    lis = "".join(
        f'<li><div><span class="t">{_e(t)}</span><p>{body}</p></div></li>' for t, body in items
    )
    return f'<ol class="ui-steps">{lis}</ol>'


def callout(body_html: str, tone: str = "neutral") -> str:
    """Tinted inline notice; ``tone`` is ok, warn, bad, info or neutral."""
    return f'<div class="ui-callout {_e(tone)}"><p>{body_html}</p></div>'


def empty_state(title: str, body_html: str) -> str:
    """Show a placeholder where a result will appear."""
    return f'<div class="ui-empty"><h4>{_e(title)}</h4><p>{body_html}</p></div>'


def legend(items: Sequence[tuple[str, str, bool]]) -> str:
    """Inline chart key of ``(colour, label, thick)`` entries."""
    spans = "".join(
        f'<span><i class="{"bar" if thick else ""}" style="background:{_e(color)}"></i>'
        f"{_e(label)}</span>"
        for color, label, thick in items
    )
    return f'<div class="ui-legend">{spans}</div>'


def signal_row_svg(offsets: Sequence[float], cycle_s: float, green_s: float) -> str:
    """Standalone animated SVG of one signal head per offset.

    Each head shows green while ``((t - O_i) mod C) < G``, matching
    :func:`traffic_coordination.signal_timing.is_green`; time runs
    ``TIME_SCALE`` times faster than the simulated corridor. The SVG carries
    its own styles so it animates when embedded as an image.
    """
    n = len(offsets)
    duration = cycle_s / TIME_SCALE
    green_pct = max(0.0, min(100.0, green_s / cycle_s * 100.0))
    width = 900
    step = width / max(n, 1)
    heads: list[str] = []
    for i, offset in enumerate(offsets):
        cx = step * (i + 0.5)
        # a negative delay starts each lamp mid-cycle, in phase from the first frame
        delay = -((cycle_s - offset % cycle_s) % cycle_s) / TIME_SCALE
        timing = f"{duration:.3f}s steps(1, end) {delay:.3f}s infinite"
        heads.append(
            f'<g transform="translate({cx:.1f},0)">'
            '<rect class="head" x="-13" y="6" width="26" height="50" rx="7"/>'
            '<circle class="off" cx="0" cy="21" r="7"/>'
            f'<circle class="stop" cx="0" cy="21" r="7" style="animation:stop {timing}"/>'
            '<circle class="off" cx="0" cy="41" r="7"/>'
            f'<circle class="go" cx="0" cy="41" r="7" style="animation:go {timing}"/>'
            '<line class="pole" x1="0" y1="56" x2="0" y2="76"/>'
            "</g>"
        )
    style = (
        f".head{{fill:{COLOR_TEXT}}}.off{{fill:#3a3f46}}"
        f".go{{fill:{COLOR_GREEN}}}.stop{{fill:{COLOR_RED}}}"
        f".pole{{stroke:{COLOR_FAINT};stroke-width:2}}.road{{stroke:{COLOR_LINE};stroke-width:2}}"
        f"@keyframes go{{0%{{opacity:1}}{green_pct:.3f}%{{opacity:0}}100%{{opacity:0}}}}"
        f"@keyframes stop{{0%{{opacity:0}}{green_pct:.3f}%{{opacity:1}}100%{{opacity:1}}}}"
        "@media (prefers-reduced-motion:reduce){circle{animation:none!important}}"
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 78">'
        f"<style>{style}</style>"
        f'<line class="road" x1="0" y1="76" x2="{width}" y2="76"/>'
        + "".join(heads)
        + "</svg>"
    )


def signal_row(offsets: Sequence[float], cycle_s: float, green_s: float) -> str:
    """Animated lights for a plan, embedded as an image so ``st.html`` keeps it."""
    svg = signal_row_svg(offsets, cycle_s, green_s)
    src = "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
    labels = "".join(
        f"<div><b>Light {i + 1}</b><span>+{offset:g} s</span></div>"
        for i, offset in enumerate(offsets)
    )
    return (
        f'<div class="ui-signals"><img src="{src}" alt="{len(offsets)} traffic lights '
        f'running the plan">'
        f'<div class="labels" style="grid-template-columns:repeat({len(offsets)},1fr)">'
        f"{labels}</div><p>Running {TIME_SCALE:g}&times; faster than real time.</p></div>"
    )
