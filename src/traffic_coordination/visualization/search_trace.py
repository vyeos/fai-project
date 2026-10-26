"""Search-trace inspection utilities and charts for the CSP solver."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from . import base_layout

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
    color_map = {
        "assign": "#1565c0",
        "reject": "#c62828",
        "fc_remove": "#00897b",
        "dead_end": "#8e24aa",
        "backtrack": "#ef6c00",
        "evaluate": "#2e7d32",
        "best": "#6a1b9a",
        "prune_bb": "#5677fcff",
        "limit": "#757575",
    }
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
                    marker=dict(size=6, color=color_map[event_type]),
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
            font=dict(color="#757575"),
        )
    fig.layout.update(
        base_layout(title="Recorded search trace: events by variable touched")
    )
    fig.update_xaxes(title="Event index (chronological)")
    fig.update_yaxes(title="Variable index", dtick=1)
    return fig


def trace_event_summary_figure(trace_dict: dict[str, object]) -> go.Figure:
    """Bar chart of recorded event counts by type."""
    counts = trace_counts(trace_dict)
    palette = [
        "#1565c0",
        "#c62828",
        "#00897b",
        "#8e24aa",
        "#ef6c00",
        "#2e7d32",
        "#6a1b9a",
        "#5c6bc0",
        "#757575",
    ]
    fig = go.Figure(
        go.Bar(x=list(counts.index), y=counts.values, marker_color=palette[: len(counts)])
    )
    fig.layout.update(base_layout(title="Search-trace event counts (within event cap)"))
    fig.update_xaxes(title="Event type")
    fig.update_yaxes(title="Count")
    return fig
