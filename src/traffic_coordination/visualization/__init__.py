"""Plotly-based visualizations for the coordination dashboard.

Design tokens (light "field notebook" palette, shared with ``ui_theme`` and
``.streamlit/config.toml``):

- surfaces: page ``#f6f6f2``, cards ``#ffffff``, hairlines ``#e2e2dc``
- text: primary ``#17191c``, muted ``#565b63``, faint ``#8b9097``
- one accent (optimizer blue) ``#2457d6``: the optimized plan, links, focus
- signal states only: go ``#1e9a5a``, stop ``#d6433b``
- vehicle directions: forward ``#2f6f8f`` (teal), reverse ``#c0682a`` (rust)
- strategies recede from light grey (no coordination) to slate (greedy) to
  the accent (optimized), so the eye lands on the optimizer first
"""

from __future__ import annotations

COLOR_BG = "#f6f6f2"
COLOR_SURFACE = "#ffffff"
COLOR_SUNKEN = "#efefea"
COLOR_LINE = "#e2e2dc"
COLOR_GRID = "#ebebe6"
COLOR_TEXT = "#17191c"
COLOR_MUTED = "#565b63"
COLOR_FAINT = "#8b9097"
COLOR_ACCENT = "#2457d6"
COLOR_GREEN = "#1e9a5a"
COLOR_GREEN_FILL = "rgba(30, 154, 90, 0.75)"
COLOR_RED = "#d6433b"
COLOR_RED_FILL = "rgba(214, 67, 59, 0.16)"
COLOR_FORWARD = "#2f6f8f"
COLOR_REVERSE = "#c0682a"
COLOR_ROAD = "#d9d9d2"
FONT = "'IBM Plex Sans', ui-sans-serif, system-ui, sans-serif"
FONT_MONO = "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace"

ALGORITHM_COLORS = {
    "uncoordinated": "#b4b8be",
    "greedy": "#5f6b7a",
    "csp": COLOR_ACCENT,
}

# Plain-language names used everywhere a strategy is shown to a reader.
ALGORITHM_LABELS = {
    "uncoordinated": "No coordination",
    "greedy": "Simple green wave",
    "csp": "Optimized search",
}

__all__ = [
    "ALGORITHM_COLORS",
    "ALGORITHM_LABELS",
    "COLOR_ACCENT",
    "COLOR_BG",
    "COLOR_FAINT",
    "COLOR_FORWARD",
    "COLOR_GREEN",
    "COLOR_GREEN_FILL",
    "COLOR_GRID",
    "COLOR_LINE",
    "COLOR_MUTED",
    "COLOR_RED",
    "COLOR_RED_FILL",
    "COLOR_REVERSE",
    "COLOR_ROAD",
    "COLOR_SUNKEN",
    "COLOR_SURFACE",
    "COLOR_TEXT",
    "FONT",
    "FONT_MONO",
    "base_layout",
    "style_figure",
]


def _axis() -> dict[str, object]:
    return {
        "gridcolor": COLOR_GRID,
        "zerolinecolor": COLOR_LINE,
        "linecolor": COLOR_LINE,
        "tickcolor": COLOR_LINE,
        "tickfont": {"family": FONT, "size": 11, "color": COLOR_MUTED},
        "title": {"font": {"size": 12, "color": COLOR_MUTED}},
        "showline": True,
        "ticks": "outside",
        "ticklen": 4,
    }


def base_layout(**overrides: object) -> object:
    """Build the common Plotly layout for all dashboard figures."""
    import plotly.graph_objects as go

    layout = {
        "font": {"family": FONT, "color": COLOR_TEXT, "size": 12},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": {"l": 56, "r": 16, "t": 44, "b": 52},
        "title": {"x": 0, "xanchor": "left", "font": {"size": 14, "color": COLOR_TEXT}},
        "xaxis": _axis(),
        "yaxis": _axis(),
        "legend": {
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"size": 12, "color": COLOR_MUTED},
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },
        "hoverlabel": {
            "bgcolor": COLOR_SURFACE,
            "bordercolor": COLOR_LINE,
            "font": {"family": FONT, "size": 12, "color": COLOR_TEXT},
        },
        "colorway": [ALGORITHM_COLORS[k] for k in ("uncoordinated", "greedy", "csp")],
    }
    title = overrides.pop("title", None)
    if isinstance(title, str):
        layout["title"] = {**layout["title"], "text": title}  # type: ignore[dict-item]
    elif title is not None:
        layout["title"] = title
    layout.update(overrides)
    return go.Layout(**layout)


def style_figure(fig: object, **overrides: object) -> object:
    """Apply the dashboard layout to an existing figure (e.g. plotly express)."""
    fig.update_layout(base_layout(**overrides))  # type: ignore[attr-defined]
    return fig
