"""Plotly-based visualizations for the coordination dashboard.

Design tokens (dark "control room" palette, shared with ``ui_theme`` and
``.streamlit/config.toml``):

- surfaces: background ``#0c0e11``, raised ``#15181d``, hairlines ``#252a31``
- text: primary ``#e4e6e9``, muted ``#8b929c``, faint ``#5c636d``
- single accent (signal amber): ``#e2a340`` -- the CSP and reverse traffic
- signal states only: go ``#4fb286``, stop ``#e0564f``
- forward vehicles: steel ``#9db7d3``
"""

from __future__ import annotations

COLOR_BG = "#0c0e11"
COLOR_SURFACE = "#15181d"
COLOR_LINE = "#252a31"
COLOR_GRID = "#1b1f25"
COLOR_TEXT = "#e4e6e9"
COLOR_MUTED = "#8b929c"
COLOR_FAINT = "#5c636d"
COLOR_ACCENT = "#e2a340"
COLOR_GREEN = "#4fb286"
COLOR_GREEN_FILL = "rgba(79, 178, 134, 0.78)"
COLOR_RED = "#e0564f"
COLOR_RED_FILL = "rgba(224, 86, 79, 0.16)"
COLOR_FORWARD = "#9db7d3"
COLOR_REVERSE = COLOR_ACCENT
COLOR_ROAD = "#2a2f37"
FONT = "Geist, ui-sans-serif, system-ui, sans-serif"
FONT_MONO = "'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace"

# Baselines recede into greys so the optimizer reads first.
ALGORITHM_COLORS = {
    "uncoordinated": "#596069",
    "greedy": "#8b929c",
    "csp": COLOR_ACCENT,
}

__all__ = [
    "ALGORITHM_COLORS",
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
        "tickfont": {"family": FONT_MONO, "size": 11, "color": COLOR_MUTED},
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
        "margin": {"l": 56, "r": 24, "t": 56, "b": 44},
        "title": {"x": 0, "xanchor": "left", "font": {"size": 14, "color": COLOR_TEXT}},
        "xaxis": _axis(),
        "yaxis": _axis(),
        "legend": {
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"size": 11, "color": COLOR_MUTED},
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
        "hoverlabel": {
            "bgcolor": COLOR_SURFACE,
            "bordercolor": COLOR_LINE,
            "font": {"family": FONT_MONO, "size": 12, "color": COLOR_TEXT},
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
