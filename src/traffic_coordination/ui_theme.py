"""Dark dashboard theme: global CSS and small HTML builders for ``app.py``.

Every function returns a string; the app decides where it renders (through
``st.html``). Inputs are escaped, numbers are formatted by the caller, and the
colour tokens are the ones in :mod:`traffic_coordination.visualization`, so
charts and chrome stay one palette.
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
    COLOR_SURFACE,
    COLOR_TEXT,
)

__all__ = [
    "GLOBAL_CSS",
    "LedgerRow",
    "callout",
    "empty_state",
    "footer",
    "headline_block",
    "hero_stat",
    "kv_grid",
    "ledger",
    "masthead",
    "signal_row_svg",
    "offset_strip",
    "overview_block",
    "prose_sections",
    "section_title",
    "spec_sheet",
    "status_pill",
]

# Real seconds of signal time per animated second in the masthead.
TIME_SCALE = 10.0

GLOBAL_CSS = f"""
<style>
:root {{
  --bg: {COLOR_BG};
  --surface: {COLOR_SURFACE};
  --surface-2: #1a1e24;
  --line: {COLOR_LINE};
  --line-soft: #1b1f25;
  --text: {COLOR_TEXT};
  --muted: {COLOR_MUTED};
  --faint: {COLOR_FAINT};
  --accent: {COLOR_ACCENT};
  --go: {COLOR_GREEN};
  --stop: {COLOR_RED};
  --lamp-off: #23272e;
  --mono: 'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
  --sans: Geist, ui-sans-serif, system-ui, sans-serif;
  --ease: cubic-bezier(0.16, 1, 0.3, 1);
}}

/* ---- canvas ---------------------------------------------------------- */
html, body, [data-testid="stAppViewContainer"] {{ background: var(--bg); }}
[data-testid="stAppViewContainer"]::after {{
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 1000;
  opacity: 0.035; mix-blend-mode: overlay;
  background-image: url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stMainBlockContainer"] {{
  max-width: 1320px; padding-top: 2.25rem; padding-bottom: 5rem;
}}
[data-testid="stMain"] p, [data-testid="stMain"] li {{ color: var(--muted); }}
[data-testid="stMain"] strong {{ color: var(--text); font-weight: 600; }}
code, [data-testid="stMain"] code {{
  font-family: var(--mono); font-size: 0.86em; color: var(--text);
  background: var(--surface); border: 1px solid var(--line-soft);
  padding: 0.08em 0.36em; border-radius: 4px;
}}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{
  color: var(--faint) !important; font-size: 0.82rem;
}}
hr {{ border-color: var(--line-soft) !important; }}

/* ---- sidebar --------------------------------------------------------- */
[data-testid="stSidebar"] {{ border-right: 1px solid var(--line-soft); }}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{ padding-top: 1.25rem; }}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
  font-family: var(--mono) !important; font-size: 0.7rem !important; font-weight: 500 !important;
  letter-spacing: 0.12em; text-transform: uppercase; color: var(--faint) !important;
  padding: 0.25rem 0 0 !important; margin: 0 !important;
}}
[data-testid="stSidebar"] label p {{ color: var(--muted) !important; font-size: 0.84rem; }}
[data-testid="stSidebar"] hr {{ margin: 1.1rem 0 !important; }}

/* ---- tabs (react-aria in Streamlit >= 1.5x; BaseWeb kept for older builds) ---- */
[data-testid="stTabs"] [role="tablist"] {{
  gap: 1.6rem; border-bottom: 1px solid var(--line-soft);
  overflow-x: auto; scrollbar-width: none;
}}
[data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar {{ display: none; }}
[data-testid="stTabs"] [role="tab"] {{
  padding: 0.7rem 0 0.8rem; height: auto; background: transparent;
}}
[data-testid="stTabs"] [role="tab"] p {{
  font-size: 0.86rem; font-weight: 450; color: var(--faint); letter-spacing: -0.005em;
  transition: color 0.3s var(--ease);
}}
[data-testid="stTabs"] [role="tab"]:hover p {{ color: var(--muted); }}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] p {{ color: var(--text); }}
[data-testid="stTabs"] .react-aria-SelectionIndicator,
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{ background: var(--accent); height: 2px; }}
[data-testid="stTabs"] [data-baseweb="tab-border"] {{ display: none; }}
[data-testid="stTabPanel"], [data-testid="stTabs"] [data-baseweb="tab-panel"] {{ padding-top: 0.75rem; }}
[data-testid="stTabPanel"] > div {{ animation: tc-rise 0.6s var(--ease) both; }}

/* ---- buttons --------------------------------------------------------- */
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-secondary"],
[data-testid="stDownloadButton"] button {{
  border-radius: 6px; font-weight: 500; letter-spacing: -0.005em;
  transition: transform 0.25s var(--ease), background-color 0.25s var(--ease),
              border-color 0.25s var(--ease), color 0.25s var(--ease);
}}
[data-testid="stBaseButton-primary"] {{
  background: var(--accent); border: 1px solid var(--accent); color: #17120a;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.22);
}}
[data-testid="stBaseButton-primary"]:hover {{
  background: #ebb257; border-color: #ebb257; color: #17120a;
}}
[data-testid="stBaseButton-primary"] p {{ color: #17120a; font-weight: 600; }}
[data-testid="stBaseButton-secondary"], [data-testid="stDownloadButton"] button {{
  background: var(--surface); border: 1px solid var(--line); color: var(--text);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
}}
[data-testid="stBaseButton-secondary"]:hover, [data-testid="stDownloadButton"] button:hover {{
  border-color: #3a404a; color: var(--text); background: var(--surface-2);
}}
button:active {{ transform: translateY(1px) scale(0.99); }}

/* ---- alerts, tables, charts ----------------------------------------- */
[data-testid="stAlertContainer"] {{
  background: var(--surface) !important; border: 1px solid var(--line-soft);
  border-left: 2px solid var(--faint); border-radius: 6px;
}}
[data-testid="stAlertContainer"] p {{ color: var(--muted) !important; }}
div[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) [data-testid="stAlertContainer"] {{
  border-left-color: var(--accent);
}}
div[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) [data-testid="stAlertContainer"] {{
  border-left-color: var(--stop);
}}
[data-testid="stDataFrame"] {{ border: 1px solid var(--line-soft); border-radius: 6px; }}
[data-testid="stExpander"] details {{
  border: 1px solid var(--line-soft); border-radius: 6px; background: transparent;
}}
[data-testid="stExpander"] summary p {{ color: var(--muted); font-size: 0.86rem; }}
[data-testid="stSlider"] [data-testid="stTickBar"] {{ font-family: var(--mono); }}
[data-baseweb="tag"] {{
  background: var(--surface-2) !important; border: 1px solid var(--line);
}}
[data-baseweb="tag"] span {{ color: var(--text) !important; font-family: var(--mono); font-size: 0.78rem; }}
[data-baseweb="tag"] svg {{ fill: var(--faint) !important; }}

/* ---- shared building blocks ----------------------------------------- */
.tc-eyebrow {{
  font-family: var(--mono); font-size: 0.7rem; letter-spacing: 0.12em;
  text-transform: uppercase; color: var(--faint);
}}
.tc-num {{ font-family: var(--mono); font-variant-numeric: tabular-nums; }}
.tc-section {{ display: flex; align-items: baseline; gap: 0.9rem; margin: 1.6rem 0 0.4rem; flex-wrap: wrap; }}
.tc-section h3 {{
  font-family: var(--sans); font-size: 1.05rem; font-weight: 600; color: var(--text);
  letter-spacing: -0.015em; margin: 0; padding: 0;
}}
.tc-section .tc-eyebrow {{ order: -1; min-width: 1.6rem; }}
.tc-section p {{ margin: 0; color: var(--faint); font-size: 0.84rem; }}

/* masthead */
.tc-mast {{
  display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
  gap: 3rem; align-items: end; padding: 0.5rem 0 2.25rem;
}}
.tc-mast h1 {{
  font-family: var(--sans); font-size: clamp(1.9rem, 3.4vw, 2.75rem); font-weight: 600;
  line-height: 1.04; letter-spacing: -0.035em; color: var(--text); margin: 0.9rem 0 1rem;
  padding: 0;
}}
.tc-mast h1 span {{ color: var(--faint); }}
.tc-mast p {{ color: var(--muted); max-width: 56ch; line-height: 1.6; margin: 0; font-size: 0.95rem; }}
.tc-wave {{
  border: 1px solid var(--line-soft); border-radius: 10px; padding: 1.1rem 1.25rem 0.9rem;
  background: linear-gradient(180deg, rgba(255,255,255,0.018), rgba(255,255,255,0));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
}}
.tc-wave-head {{ display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; white-space: nowrap; }}
.tc-wave-head b {{ color: var(--text); font-weight: 500; }}
.tc-wave img {{ width: 100%; height: auto; display: block; margin-top: 0.9rem; }}
.tc-wave-labels {{ display: grid; margin-top: 0.55rem; text-align: center; }}
.tc-wave-labels b {{ display: block; font-family: var(--mono); font-size: 0.72rem; font-weight: 500; color: var(--muted); }}
.tc-wave-labels span {{ font-family: var(--mono); font-size: 0.68rem; color: var(--faint); }}
.tc-live {{ display: inline-flex; align-items: center; gap: 0.45rem; }}
.tc-live i {{
  width: 6px; height: 6px; border-radius: 50%; background: var(--go);
  animation: tc-breathe 2.4s ease-in-out infinite;
}}

/* spec sheet + hero stat */
.tc-overview {{
  display: grid; grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.25fr); gap: 3.5rem;
  padding: 1.6rem 0 2.5rem; border-bottom: 1px solid var(--line-soft); margin-bottom: 0.5rem;
}}
.tc-hero {{ display: flex; flex-direction: column; gap: 0.6rem; }}
.tc-hero .value {{
  font-family: var(--mono); font-size: clamp(2.6rem, 5vw, 3.6rem); font-weight: 500;
  letter-spacing: -0.04em; line-height: 1; color: var(--text); font-variant-numeric: tabular-nums;
}}
.tc-hero .value small {{ font-size: 0.4em; color: var(--faint); letter-spacing: 0; margin-left: 0.4rem; }}
.tc-hero .note {{ color: var(--muted); font-size: 0.88rem; line-height: 1.55; max-width: 42ch; }}
.tc-hero .note code {{ font-size: 0.82em; }}
.tc-spec {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 2.5rem; margin: 0; }}
.tc-spec div {{
  display: flex; justify-content: space-between; align-items: baseline; gap: 1rem;
  padding: 0.72rem 0; border-top: 1px solid var(--line-soft);
}}
.tc-spec dt {{ color: var(--faint); font-size: 0.84rem; }}
.tc-spec dd {{ margin: 0; color: var(--text); font-family: var(--mono); font-size: 0.88rem; text-align: right; }}

/* status pill */
.tc-pill {{
  display: inline-flex; align-items: center; gap: 0.4rem; white-space: nowrap;
  font-family: var(--mono); font-size: 0.7rem; letter-spacing: 0.02em; color: var(--muted);
  padding: 0.18rem 0.5rem; border: 1px solid var(--line); border-radius: 999px;
}}
.tc-pill i {{ width: 5px; height: 5px; border-radius: 50%; background: var(--faint); }}
.tc-pill.ok i {{ background: var(--go); }}
.tc-pill.warn i {{ background: var(--accent); }}
.tc-pill.bad i {{ background: var(--stop); }}

/* comparison ledger */
.tc-ledger {{ width: 100%; }}
.tc-ledger .row {{
  display: grid; align-items: center; gap: 1.25rem;
  grid-template-columns: minmax(9rem, 1.1fr) repeat(3, minmax(4.5rem, 0.5fr)) minmax(8rem, 1.6fr);
  padding: 0.95rem 0; border-top: 1px solid var(--line-soft);
  animation: tc-rise 0.7s var(--ease) both; animation-delay: calc(var(--i, 0) * 70ms);
}}
.tc-ledger .row.head {{ border-top: 0; padding: 0 0 0.55rem; animation: none; }}
.tc-ledger .row.head span {{
  font-family: var(--mono); font-size: 0.68rem; letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--faint);
}}
.tc-ledger .name {{ display: flex; flex-direction: column; gap: 0.35rem; align-items: flex-start; }}
.tc-ledger .name b {{ color: var(--text); font-weight: 500; font-size: 0.95rem; }}
.tc-ledger .n {{ font-family: var(--mono); font-variant-numeric: tabular-nums; color: var(--muted); text-align: right; font-size: 0.9rem; }}
.tc-ledger .row.best .n.j {{ color: var(--text); }}
.tc-ledger .bar {{ height: 6px; background: var(--line-soft); border-radius: 3px; overflow: hidden; }}
.tc-ledger .bar i {{
  display: block; height: 100%; border-radius: 3px; transform-origin: left center;
  animation: tc-grow 1.1s var(--ease) both; animation-delay: calc(var(--i, 0) * 90ms + 120ms);
}}
.tc-ledger .row.head .r {{ text-align: right; }}

/* offset strip */
.tc-offsets {{ display: grid; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); border-top: 1px solid var(--line-soft); }}
.tc-offsets div {{ padding: 0.8rem 0.9rem 0.2rem 0; border-right: 1px solid var(--line-soft); margin-right: 0.9rem; }}
.tc-offsets div:last-child {{ border-right: 0; margin-right: 0; }}
.tc-offsets span {{ display: block; font-family: var(--mono); font-size: 0.7rem; color: var(--faint); letter-spacing: 0.08em; }}
.tc-offsets b {{ font-family: var(--mono); font-size: 1.25rem; font-weight: 500; color: var(--text); letter-spacing: -0.02em; }}
.tc-offsets b small {{ font-size: 0.6em; color: var(--faint); margin-left: 0.15rem; }}

/* key/value grid */
.tc-kv {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(13rem, 1fr)); column-gap: 2rem; }}
.tc-kv div {{ padding: 0.75rem 0; border-top: 1px solid var(--line-soft); display: flex; flex-direction: column; gap: 0.3rem; min-width: 0; }}
.tc-kv span {{ font-size: 0.78rem; color: var(--faint); }}
.tc-kv b {{ font-family: var(--mono); font-weight: 500; color: var(--text); font-size: 0.95rem; overflow-wrap: anywhere; }}

/* callout + empty state */
.tc-callout {{
  display: grid; grid-template-columns: auto 1fr; gap: 0.9rem; align-items: start;
  padding: 1rem 1.1rem; border: 1px solid var(--line-soft); border-radius: 8px; background: var(--surface);
}}
.tc-callout i {{ width: 8px; height: 8px; border-radius: 50%; margin-top: 0.45rem; background: var(--faint); }}
.tc-callout.ok i {{ background: var(--go); }}
.tc-callout.warn i {{ background: var(--accent); }}
.tc-callout.bad i {{ background: var(--stop); }}
.tc-callout p {{ margin: 0; color: var(--muted); line-height: 1.55; font-size: 0.9rem; }}
.tc-callout b {{ color: var(--text); font-weight: 500; }}
.tc-empty {{
  display: grid; grid-template-columns: 2.25rem 1fr; gap: 1.1rem; align-items: start;
  padding: 1.6rem 0 1rem; border-top: 1px dashed var(--line);
}}
.tc-empty img {{ width: 2.25rem; height: 2.25rem; }}
.tc-empty h4 {{ margin: 0 0 0.35rem; padding: 0; color: var(--text); font-size: 0.98rem; font-weight: 500; font-family: var(--sans); }}
.tc-empty p {{ margin: 0; color: var(--muted); font-size: 0.88rem; line-height: 1.55; max-width: 60ch; }}

/* results headline */
.tc-headline {{
  display: grid; grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr); gap: 3rem; align-items: end;
  padding: 1.6rem 0 2rem; border-bottom: 1px solid var(--line-soft); margin-bottom: 0.5rem;
}}

/* learn */
.tc-prose {{ max-width: 860px; }}
.tc-prose section {{
  display: grid; grid-template-columns: 3.25rem minmax(0, 1fr); gap: 1.25rem;
  padding: 1.5rem 0; border-top: 1px solid var(--line-soft);
}}
.tc-prose section > span {{ font-family: var(--mono); font-size: 0.78rem; color: var(--accent); padding-top: 0.2rem; }}
.tc-prose h4 {{ margin: 0 0 0.55rem; padding: 0; font-family: var(--sans); font-size: 1rem; font-weight: 600; color: var(--text); letter-spacing: -0.01em; }}
.tc-prose p, .tc-prose li {{ color: var(--muted); line-height: 1.65; font-size: 0.92rem; margin: 0; max-width: 68ch; }}
.tc-prose ul {{ margin: 0.2rem 0 0; padding-left: 1.1rem; }}
.tc-prose li + li {{ margin-top: 0.2rem; }}

.tc-foot {{ margin-top: 3rem; padding-top: 1.1rem; border-top: 1px solid var(--line-soft);
  display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap; }}
.tc-foot span {{ font-family: var(--mono); font-size: 0.7rem; color: var(--faint); letter-spacing: 0.04em; }}

@keyframes tc-rise {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes tc-grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
@keyframes tc-breathe {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.35; }} }}

@media (max-width: 767px) {{
  [data-testid="stMainBlockContainer"] {{ padding-left: 1rem; padding-right: 1rem; }}
  .tc-mast, .tc-overview, .tc-headline {{ grid-template-columns: 1fr; gap: 1.75rem; }}
  .tc-spec {{ grid-template-columns: 1fr; }}
  .tc-ledger .row {{ grid-template-columns: minmax(0, 1fr) repeat(3, auto); }}
  .tc-ledger .bar {{ grid-column: 1 / -1; }}
  .tc-ledger .row.head span:last-child {{ display: none; }}
  .tc-offsets {{ grid-auto-flow: row; grid-template-columns: repeat(3, minmax(0, 1fr)); }}
  .tc-prose section {{ grid-template-columns: 1fr; gap: 0.4rem; }}
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation: none !important; transition: none !important; }}
}}
</style>
"""


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def section_title(title: str, index: str | None = None, note: str | None = None) -> str:
    """Section heading: optional mono index, title, optional faint note."""
    idx = f'<span class="tc-eyebrow">{_e(index)}</span>' if index else ""
    tail = f"<p>{_e(note)}</p>" if note else ""
    return f'<div class="tc-section">{idx}<h3>{_e(title)}</h3>{tail}</div>'


def status_pill(text: str, tone: str = "neutral") -> str:
    """Small rounded status label; ``tone`` is ok, warn, bad or neutral."""
    return f'<span class="tc-pill {_e(tone)}"><i></i>{_e(text)}</span>'


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
    step = 420 / max(n, 1)
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
        f".head{{fill:#121519;stroke:{COLOR_LINE}}}.off{{fill:#23272e}}"
        f".go{{fill:{COLOR_GREEN}}}.stop{{fill:{COLOR_RED}}}.pole,.road{{stroke:{COLOR_LINE}}}"
        f"@keyframes go{{0%{{opacity:1}}{green_pct:.3f}%{{opacity:0}}100%{{opacity:0}}}}"
        f"@keyframes stop{{0%{{opacity:0}}{green_pct:.3f}%{{opacity:1}}100%{{opacity:1}}}}"
        "@media (prefers-reduced-motion:reduce){circle{animation:none!important}}"
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 78">'
        f"<style>{style}</style>"
        '<line class="road" x1="0" y1="76" x2="420" y2="76"/>'
        + "".join(heads)
        + "</svg>"
    )


def masthead(
    offsets: Sequence[float] | None,
    cycle_s: float,
    green_s: float,
    plan_label: str,
    eyebrow: str,
) -> str:
    """Title block plus a live signal row that runs ``offsets`` in real time.

    With ``offsets`` set to None (an invalid scenario) only the title renders.
    """
    copy = (
        f'<div><div class="tc-eyebrow">{_e(eyebrow)}</div>'
        "<h1>Signal coordination<br><span>on an arterial corridor.</span></h1>"
        "<p>Three strategies plan the signal offsets for the same simulated traffic: "
        "no coordination, greedy progression, and a CSP solver with forward checking "
        "and branch and bound. Every figure here comes from the simulator, "
        "not from a real street.</p></div>"
    )
    if offsets is None:
        return f'<header class="tc-mast">{copy}</header>'
    svg = signal_row_svg(offsets, cycle_s, green_s)
    src = "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
    labels = "".join(
        f"<div><b>I{i + 1}</b><span>+{offset:g}s</span></div>" for i, offset in enumerate(offsets)
    )
    return (
        f'<header class="tc-mast">{copy}<div class="tc-wave"><div class="tc-wave-head">'
        f'<span class="tc-eyebrow tc-live"><i></i>{_e(plan_label)}</span>'
        f'<span class="tc-eyebrow">C {cycle_s:g}s &middot; G {green_s:g}s &middot; '
        f"&times;{TIME_SCALE:g}</span></div>"
        f'<img src="{src}" alt="{len(offsets)} signal heads running the {_e(plan_label)}">'
        f'<div class="tc-wave-labels" style="grid-template-columns:repeat({len(offsets)},1fr)">'
        f"{labels}</div></div></header>"
    )


def hero_stat(eyebrow: str, value: str, unit: str, note_html: str) -> str:
    """One large mono figure with a caption. ``note_html`` is trusted markup."""
    return (
        '<div class="tc-hero">'
        f'<span class="tc-eyebrow">{_e(eyebrow)}</span>'
        f'<span class="value">{_e(value)}<small>{_e(unit)}</small></span>'
        f'<span class="note">{note_html}</span>'
        "</div>"
    )


def spec_sheet(rows: Sequence[tuple[str, str]]) -> str:
    """Two-column definition list of scenario parameters."""
    items = "".join(f"<div><dt>{_e(k)}</dt><dd>{_e(v)}</dd></div>" for k, v in rows)
    return f'<dl class="tc-spec">{items}</dl>'


def overview_block(hero_html: str, spec_html: str) -> str:
    """Asymmetric two-column overview: hero figure left, spec sheet right."""
    return f'<div class="tc-overview">{hero_html}{spec_html}</div>'


def headline_block(left_html: str, right_html: str) -> str:
    """Results headline: big figure left, verification statement right."""
    return f'<div class="tc-headline">{left_html}<div>{right_html}</div></div>'


@dataclass(frozen=True)
class LedgerRow:
    """One algorithm's line in the comparison ledger."""

    algorithm: str
    status: str
    tone: str
    waiting_s: float
    stops: int
    objective: float


def ledger(rows: Sequence[LedgerRow]) -> str:
    """Comparison table with an objective bar per algorithm; lowest J is marked."""
    if not rows:
        return ""
    worst = max(r.objective for r in rows) or 1.0
    best = min(r.objective for r in rows)
    head = (
        '<div class="row head"><span>Strategy</span><span class="r">Wait s</span>'
        '<span class="r">Stops</span><span class="r">J</span><span>Objective</span></div>'
    )
    body = []
    for i, r in enumerate(rows):
        color = ALGORITHM_COLORS.get(r.algorithm, COLOR_MUTED)
        width = max(r.objective / worst * 100.0, 0.6)
        cls = "row best" if r.objective == best else "row"
        body.append(
            f'<div class="{cls}" style="--i:{i}">'
            f'<div class="name"><b>{_e(r.algorithm)}</b>{status_pill(r.status, r.tone)}</div>'
            f'<span class="n">{r.waiting_s:,.0f}</span>'
            f'<span class="n">{r.stops:,}</span>'
            f'<span class="n j">{r.objective:,.0f}</span>'
            f'<div class="bar"><i style="width:{width:.2f}%;background:{color}"></i></div>'
            "</div>"
        )
    return f'<div class="tc-ledger">{head}{"".join(body)}</div>'


def offset_strip(offsets: Sequence[float]) -> str:
    """Horizontal strip of per-intersection offsets."""
    cells = "".join(
        f"<div><span>I{i + 1}</span><b>{o:g}<small>s</small></b></div>"
        for i, o in enumerate(offsets)
    )
    return f'<div class="tc-offsets">{cells}</div>'


def kv_grid(items: Sequence[tuple[str, str]]) -> str:
    """Responsive grid of label/value pairs (search statistics)."""
    cells = "".join(f"<div><span>{_e(k)}</span><b>{_e(v)}</b></div>" for k, v in items)
    return f'<div class="tc-kv">{cells}</div>'


def callout(body_html: str, tone: str = "neutral") -> str:
    """Inline statement with a coloured status dot. ``body_html`` is trusted."""
    return f'<div class="tc-callout {_e(tone)}"><i></i><p>{body_html}</p></div>'


_EMPTY_ICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 36 36" fill="none" '
    f'stroke="{COLOR_FAINT}" stroke-width="1.5">'
    '<rect x="11" y="3" width="14" height="30" rx="5"/>'
    '<circle cx="18" cy="11" r="3"/><circle cx="18" cy="18" r="3"/>'
    f'<circle cx="18" cy="25" r="3" stroke="{COLOR_ACCENT}"/></svg>'
)
_EMPTY_ICON = (
    '<img alt="" src="data:image/svg+xml;base64,'
    + base64.b64encode(_EMPTY_ICON_SVG.encode("utf-8")).decode("ascii")
    + '">'
)


def empty_state(title: str, body_html: str) -> str:
    """Composed empty state with a signal-head glyph. ``body_html`` is trusted."""
    return (
        f'<div class="tc-empty">{_EMPTY_ICON}<div><h4>{_e(title)}</h4>'
        f"<p>{body_html}</p></div></div>"
    )


def prose_sections(sections: Sequence[tuple[str, str]]) -> str:
    """Numbered long-form sections; each body is trusted markup."""
    parts = "".join(
        f"<section><span>{i + 1:02d}</span><div><h4>{_e(title)}</h4>{body}</div></section>"
        for i, (title, body) in enumerate(sections)
    )
    return f'<div class="tc-prose">{parts}</div>'


def footer(left: str, right: str) -> str:
    """Thin mono footer line."""
    return f'<div class="tc-foot"><span>{_e(left)}</span><span>{_e(right)}</span></div>'

