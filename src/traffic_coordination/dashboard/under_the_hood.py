"""Page 4: the raw search numbers, the independent check and downloads."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from traffic_coordination import ui_theme as ui
from traffic_coordination.metrics import results_dataframe
from traffic_coordination.ui_state import RunBundle
from traffic_coordination.visualization import search_trace as traceviz

from . import common


def check_section(bundle: RunBundle) -> None:
    """Whether a brute-force enumeration confirmed the optimizer's answer."""
    st.html(
        ui.section(
            "Was the answer double-checked?",
            "When the number of plans is small enough, a separate, deliberately simple "
            "program scores every allowed plan one by one and compares its best with the "
            "optimizer's.",
            first=True,
        )
    )
    ver = bundle.verification
    score = bundle.csp.simulation.objective
    if ver is not None and ver.completed and ver.best_offsets is not None:
        if abs(ver.best_objective - score) < 1e-9:
            text, tone = (
                f"<b>Yes, confirmed.</b> Scoring all {ver.feasible_plans:,} allowed plans "
                f"gives the same best score, {ver.best_objective:,.0f}.",
                "ok",
            )
        else:
            text, tone = (
                "<b>No, they disagree.</b> Brute force found a better plan than the "
                "optimizer. That would be a bug in the search.",
                "bad",
            )
    elif ver is not None:
        text, tone = (
            "<b>Not finished.</b> The brute-force check ran out of its 60 s budget, so the "
            "result is not independently confirmed.",
            "warn",
        )
    else:
        text, tone = (
            f"<b>Skipped.</b> This road has {bundle.config.search_space_size:,} possible "
            "plans, too many to score one by one here. The optimizer's own guarantee "
            "still applies when its status is “Best possible”.",
            "neutral",
        )
    st.html(ui.callout(text, tone))


def effort_section(bundle: RunBundle) -> None:
    """Search counters, each with what it means."""
    stats = bundle.csp.metadata.get("search_stats", {})
    space = int(stats.get("search_space_size", bundle.config.search_space_size))
    scored = int(stats.get("complete_assignments_evaluated", 0))
    share = scored / space * 100 if space else 0.0
    st.html(
        ui.section(
            "How much searching it took",
            f"The optimizer scored <b>{scored:,}</b> of {space:,} possible plans "
            f"({share:.2g}%) and ruled out the rest without simulating them.",
        )
    )

    def n(key: str) -> str:
        return f"{int(stats.get(key, 0)):,}"

    st.html(
        ui.terms(
            [
                ("Possible plans", f"{space:,}", "Every combination of offsets, before any rule is applied."),
                ("Plans scored", n("complete_assignments_evaluated"), "Complete plans that were run through the simulator."),
                ("Values tried", n("assignments_attempted"), "Times the search gave one light one offset."),
                ("Ruled out ahead", n("forward_check_removals"), "Offsets crossed out by forward checking because they would break the green-wave rule."),
                ("Dead ends", n("dead_ends"), "Times a light was left with no allowed offset, so the search backed up at once."),
                ("Branches explored", n("nodes_expanded"), "Partial plans the search extended by one more light."),
                ("Skipped by bound", n("branch_bound_prunes"), "Branches dropped because they could not beat the best plan so far. Usually 0: the bound is safe but cautious."),
                ("Search time", f"{float(stats.get('search_time_s', bundle.csp.search_time_s)):.2f} s", "Wall-clock time of the search, including simulating every scored plan."),
            ]
        )
    )


def trace_section(bundle: RunBundle) -> None:
    """Charts and table of the recorded search steps."""
    trace = bundle.csp_trace
    events = trace.get("events", []) if isinstance(trace, dict) else []
    st.html(
        ui.section(
            "The search, step by step",
            "The optimizer records what it does at each step. Left: how often each kind of "
            "step happened. Right: which light it was working on at each step. Moving up "
            "is going deeper into the tree; dropping back down is backtracking.",
            f"Only the first {len(events):,} steps are recorded"
            + (" (the search went on after that)." if trace.get("truncated") else "."),
        )
    )
    if not events:
        st.html(ui.empty_state("No steps recorded", "This run did not record a trace."))
        return
    left, right = st.columns(2, gap="medium")
    with left:
        common.chart(traceviz.trace_event_summary_figure(trace), key="trace_counts")
    with right:
        common.chart(traceviz.trace_depth_figure(trace), key="trace_depth")
    table = pd.DataFrame(
        {
            "Step": range(1, len(events) + 1),
            "What happened": [traceviz.EVENT_LABELS.get(e.get("type"), e.get("type")) for e in events],
            "Light": [
                f"Light {e['var'] + 1}" if isinstance(e.get("var"), int) else "" for e in events
            ],
            "Offset": [f"{e['value']:g} s" if "value" in e else "" for e in events],
            "Plan": [
                " / ".join(f"{o:g}" for o in e["offsets"]) if e.get("offsets") else "" for e in events
            ],
            "Score": [f"{e['objective']:,.0f}" if "objective" in e else "" for e in events],
        }
    )
    st.dataframe(table, hide_index=True, width="stretch", height=360)


def download_section(bundle: RunBundle) -> None:
    """Files holding this run's actual results."""
    config = bundle.config
    st.html(
        ui.section(
            "Download this run",
            "The same numbers shown on these pages, for a spreadsheet or your own analysis.",
        )
    )
    plans = {
        r.algorithm: {"offsets": list(r.plan.offsets), "status": r.status} for r in bundle.results
    }
    trace_frame = traceviz.trace_dataframe(bundle.csp_trace)
    files = [
        ("Results table", "CSV", results_dataframe(bundle.results).to_csv(index=False), "results.csv", "text/csv"),
        ("Timing plans", "JSON", json.dumps({"config": config.to_dict(), "plans": plans}, indent=2), "timing_plans.json", "application/json"),
        ("Search steps", "CSV", trace_frame.to_csv(index=False), "search_steps.csv", "text/csv"),
    ]
    columns = st.columns(len(files), gap="small")
    for column, (label, kind, data, name, mime) in zip(columns, files, strict=True):
        with column:
            st.download_button(
                f"{label} ({kind})", data.encode("utf-8"), file_name=name, mime=mime, width="stretch"
            )


def settings_section(bundle: RunBundle) -> None:
    """Every scenario parameter used for this run."""
    c = bundle.config
    tol = f"±{c.progression_tolerance_s:g} s" if c.progression_tolerance_s is not None else "Off"
    st.html(ui.section("Settings used for this run"))
    rows = [
        ["Traffic lights", f"{c.n_intersections}", "Signals on the road"],
        ["Distance between lights", f"{c.link_distance_m:g} m", "Same for every gap"],
        ["Speed limit", f"{c.speed_kmh:g} km/h", "Every car drives at exactly this speed"],
        ["Cars", f"{c.vehicles_per_direction} per direction", "Both ways" if c.direction_mode == "both" else "One way"],
        ["Arrivals", "In a bunch" if c.departure_pattern == "platoon" else "Spread out", f"{c.headway_s:g} s apart at the closest"],
        ["Cycle / green", f"{c.cycle_length:g} s / {c.green_duration:g} s", "Shared by all lights"],
        ["Timing step", f"{c.offset_resolution_s:g} s", f"{c.offsets_per_intersection} choices per light"],
        ["Green-wave rule", tol, "Allowed gap from the driving time"],
        ["Score", f"wait + {c.objective_weight_stop:g} × stops", f"Wait weight {c.objective_weight_wait:g}"],
        ["Search limits", f"{common.TIME_BUDGET_S:g} s, {common.EVALUATION_CAP:,} plans", "The search reports if it hits either"],
    ]
    st.html(ui.plan_table(["Setting", "Value", "Note"], rows))


def render() -> None:
    """Draw the page."""
    bundle = common.current_bundle()
    st.html(
        ui.page_header(
            "Under the hood",
            "The raw numbers behind your last run: whether the answer was checked, how "
            "much searching it took, every recorded step, and files to download. "
            f"Road: {common.road_sentence(bundle.config)}",
        )
    )
    check_section(bundle)
    effort_section(bundle)
    trace_section(bundle)
    download_section(bundle)
    settings_section(bundle)
