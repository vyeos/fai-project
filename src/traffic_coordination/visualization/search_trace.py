"""Search-trace inspection utilities and charts for the CSP solver."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from . import (
    COLOR_ACCENT,
    COLOR_FAINT,
    COLOR_FORWARD,
    COLOR_GREEN,
    COLOR_MUTED,
    COLOR_RED,
    base_layout,
)

# Event palette: the accent marks the incumbent ('best'); greys carry the bulk.
EVENT_COLORS = {
    "assign": COLOR_FORWARD,
    "reject": COLOR_RED,
    "fc_remove": "#7aa59a",
    "dead_end": "#a0675f",
    "backtrack": COLOR_MUTED,
    "evaluate": COLOR_GREEN,
    "best": COLOR_ACCENT,
    "prune_bb": "#9aa0a8",
    "limit": COLOR_FAINT,
}

# Plain-language names for the event types the solver records.
EVENT_LABELS = {
    "assign": "Tried a value",
    "reject": "Broke the timing rule",
    "fc_remove": "Ruled out ahead",
    "dead_end": "Dead end",
    "backtrack": "Backtracked",
    "evaluate": "Scored a full plan",
    "best": "New best plan",
    "prune_bb": "Skipped by bound",
    "limit": "Stopped by limit",
}

__all__ = [
    "EVENT_LABELS",
    "trace_dataframe",
    "trace_counts",
    "trace_depth_figure",
    "trace_event_summary_figure",
]


EVENT_TYPES = (
    "assign",
    "reject",
    "fc_remove",
    "dead_end",
    "backtrack",
    "evaluate",
    "best",
    "prune_bb",
    "limit",
)


def trace_dataframe(trace_dict: dict[str, object]) -> pd.DataFrame:
    """Flatten the trace events into a DataFrame for display/export."""
    events = trace_dict.get("events", []) if isinstance(trace_dict, dict) else []
    rows = [
        {
            "event_index": idx,
            **{k: v for k, v in event.items() if k != "type"},
            "type": event.get("type"),
        }
        for idx, event in enumerate(events)
    ]
    return pd.DataFrame(rows)


def trace_counts(trace_dict: dict[str, object]) -> pd.Series:
    """Count recorded events by type (from the *capped* trace)."""
    events = trace_dict.get("events", []) if isinstance(trace_dict, dict) else []
    counts = pd.Series([e.get("type", "?") for e in events]).value_counts()
    return counts


def trace_depth_figure(trace_dict: dict[str, object]) -> go.Figure:
    """Scatter of recorded assign/backtrack events along the event index axis.

    Each event is placed at the depth it touched; gaps indicate the event cap
    (also annotated). This is an *inspection aid* for a limited window of the
    search, not a full-tree rendering (impractical for large searches).
    """
    events = trace_dict.get("events", []) if isinstance(trace_dict, dict) else []
    fig = go.Figure()
    color_map = EVENT_COLORS
    for event_type in color_map:
        matching = [e for e in events if e.get("type") == event_type]
        xs = [i for i, e in enumerate(events) if e.get("type") == event_type]
        # scored plans happen at full depth, after the last light is set
        ys = [
            e["var"] if "var" in e else len(e.get("offsets", ())) - 1 if "offsets" in e else -1
            for e in matching
        ]
        if xs:
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=[y + 1 for y in ys],
                    mode="markers",
                    marker=dict(size=5, color=color_map[event_type], opacity=0.9),
                    name=EVENT_LABELS.get(event_type, event_type),
                    hovertemplate="%{customdata}<extra></extra>",
                    customdata=[str({k: v for k, v in e.items() if k != "type"}) for e in matching],
                )
            )
    if trace_dict.get("truncated"):
        fig.add_annotation(
            x=1,
            xref="x",
            y=0,
            text="trace truncated at event cap",
            showarrow=False,
            font=dict(color=COLOR_FAINT),
        )
    fig.layout.update(
        base_layout(height=380, margin={"l": 72, "r": 16, "t": 64, "b": 52})
    )
    fig.update_xaxes(title="Step of the search")
    fig.update_yaxes(title="Light being timed", dtick=1, tickprefix="Light ")
    return fig


def trace_event_summary_figure(trace_dict: dict[str, object]) -> go.Figure:
    """Bar chart of recorded event counts by type."""
    counts = trace_counts(trace_dict)
    fig = go.Figure(
        go.Bar(
            x=[EVENT_LABELS.get(str(k), str(k)) for k in counts.index],
            y=counts.values,
            marker_color=[EVENT_COLORS.get(str(k), COLOR_FAINT) for k in counts.index],
            marker_line_width=0,
        )
    )
    fig.layout.update(base_layout(height=380, margin={"l": 56, "r": 16, "t": 64, "b": 52}))
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="Times recorded")
    return fig
