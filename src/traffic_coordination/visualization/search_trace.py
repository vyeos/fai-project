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
    "fc_remove": "#5f8f86",
    "dead_end": "#a0675f",
    "backtrack": COLOR_MUTED,
    "evaluate": COLOR_GREEN,
    "best": COLOR_ACCENT,
    "prune_bb": "#c9cdd3",
    "limit": COLOR_FAINT,
}

__all__ = [
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
        ys = [e.get("var", e.get("next_var", -1)) for e in matching]
        if xs:
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="markers",
                    marker=dict(size=5, color=color_map[event_type], opacity=0.9),
                    name=event_type,
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
        base_layout(title="Events by variable touched", height=380)
    )
    fig.update_xaxes(title="Event index (chronological)")
    fig.update_yaxes(title="Variable index", dtick=1)
    return fig


def trace_event_summary_figure(trace_dict: dict[str, object]) -> go.Figure:
    """Bar chart of recorded event counts by type."""
    counts = trace_counts(trace_dict)
    fig = go.Figure(
        go.Bar(
            x=list(counts.index),
            y=counts.values,
            marker_color=[EVENT_COLORS.get(str(k), COLOR_FAINT) for k in counts.index],
            marker_line_width=0,
        )
    )
    fig.layout.update(base_layout(title="Event counts (within event cap)", height=380))
    fig.update_xaxes(title="Event type")
    fig.update_yaxes(title="Count")
    return fig
