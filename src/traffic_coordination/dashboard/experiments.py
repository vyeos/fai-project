"""Page 3: saved benchmark scenarios and live one-factor sweeps."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from traffic_coordination import ui_theme as ui
from traffic_coordination.config import ScenarioConfig
from traffic_coordination.metrics import FEASIBLE_OPTIMAL
from traffic_coordination.ui_state import cached_run
from traffic_coordination.visualization import ALGORITHM_COLORS, ALGORITHM_LABELS, style_figure

from . import common

RESULTS_CSV = (
    Path(__file__).resolve().parents[3] / "experiments" / "results" / "benchmark_results.csv"
)
MAIN = ("A", "B", "C", "D", "E")

SCENARIO_TEXT = {
    "A": "3 lights, light traffic: a small road where every plan can be checked.",
    "B": "5 lights, moderate traffic: the default road on the first page.",
    "C": "7 lights, moderate traffic: almost 3 million plans, so the green-wave rule is on.",
    "D": "5 lights, heavy traffic: 100 cars instead of 40.",
    "E": "5 lights with a 1 s timing step: 12 times finer choices, rule on.",
}

# label -> (values, how to apply a value to a config, x-axis title)
SWEEPS: dict[str, tuple[list[float], str, str]] = {
    "Amount of traffic": ([5, 10, 20, 30, 50], "vehicles_per_direction", "Cars in each direction"),
    "Speed limit": ([25, 30, 40, 50, 60], "speed_kmh", "Speed limit (km/h)"),
    "Number of lights": ([3, 4, 5, 6, 7], "n_intersections", "Number of lights"),
    "Distance between lights": ([200, 300, 400, 500, 600], "link_distance_m", "Distance (m)"),
}
SWEEP_KEY = "sweep"
SWEEP_BUDGET_S = 5.0
SWEEP_CAP = 30_000


@st.cache_data(show_spinner=False)
def load_benchmarks(path: str) -> pd.DataFrame | None:
    """Load saved benchmark rows, or None when the file is missing."""
    p = Path(path)
    return pd.read_csv(p) if p.exists() else None


def benchmark_section() -> None:
    """Table and chart of the saved A-E benchmark results."""
    st.html(
        ui.section(
            "Five test roads",
            "These roads were run ahead of time with the repository's benchmark script. "
            "Each one changes a single thing from the default road, so you can see when "
            "the optimizer helps most.",
            first=True,
        )
    )
    frame = load_benchmarks(str(RESULTS_CSV))
    if frame is None:
        st.html(
            ui.empty_state(
                "No saved results found",
                "Run <code>python -m traffic_coordination.experiments.benchmark_runner "
                "--all</code> to create them.",
            )
        )
        return
    frame = frame[frame["scenario"].isin(MAIN)].copy()
    frame["wait_per_car"] = frame["total_waiting_time_s"] / frame["n_vehicles"]
    rows = []
    for name in MAIN:
        group = frame[frame["scenario"] == name].set_index("algorithm")
        if group.empty:
            continue
        base = group.loc["uncoordinated", "objective"]
        best = group.loc["csp", "objective"]
        checked = bool(group.loc["csp", "csp_matches_brute_force"]) and bool(
            group.loc["csp", "exhaustive_completed"]
        )
        proof = (
            "Checked by brute force"
            if checked
            else "Proven by the search"
            if group.loc["csp", "status"] == FEASIBLE_OPTIMAL
            else "Not proven"
        )
        rows.append(
            [
                name,
                SCENARIO_TEXT.get(name, ""),
                f"{base:,.0f}",
                f"{group.loc['greedy', 'objective']:,.0f}",
                f"{best:,.0f}",
                f"{(base - best) / base * 100:.0f}% lower",
                proof,
            ]
        )
    st.html(
        ui.plan_table(
            [
                "Road",
                "What it tests",
                "No coordination",
                "Simple green wave",
                "Optimized",
                "Optimized vs none",
                "Is it the best?",
            ],
            rows,
            numeric=4,
        )
    )
    st.caption(
        "Scores: total waiting seconds plus 2 s per stop (lower is better). "
        "“Checked by brute force” means a separate program scored every allowed plan and "
        "found the same best score."
    )
    chart_frame = frame.assign(strategy=frame["algorithm"].map(ALGORITHM_LABELS))
    fig = px.bar(
        chart_frame,
        x="scenario",
        y="wait_per_car",
        color="strategy",
        barmode="group",
        color_discrete_map={ALGORITHM_LABELS[k]: v for k, v in ALGORITHM_COLORS.items()},
        category_orders={"strategy": list(ALGORITHM_LABELS.values())},
    )
    style_figure(fig, height=360, bargap=0.25, margin={"l": 56, "r": 16, "t": 36, "b": 52})
    fig.update_traces(marker_line_width=0, hovertemplate="%{y:.1f} s<extra></extra>")
    fig.update_xaxes(title="Test road")
    fig.update_yaxes(title="Waiting per car (s)")
    fig.update_layout(legend_title_text="")
    common.chart(fig, key="bench_chart")


def variant(config: ScenarioConfig, field: str, value: float) -> ScenarioConfig:
    """Copy ``config`` with one field changed (validated again)."""
    cast = int(value) if field in ("vehicles_per_direction", "n_intersections") else float(value)
    extra = {"demand_level": "custom"} if field == "vehicles_per_direction" else {}
    return replace(config, **{field: cast, **extra})


def sweep_section(config: ScenarioConfig) -> None:
    """Re-run all strategies while one factor of the reader's road changes."""
    st.html(
        ui.section(
            "What changes the result?",
            "Pick one thing to vary. Everything else stays as on your road "
            f"({common.road_sentence(config)}) and all three strategies are re-run for "
            "each value.",
        )
    )
    factor = st.radio("Vary", list(SWEEPS), horizontal=True, key="sweep_factor")
    values, field, axis_title = SWEEPS[factor]
    if st.button("Run comparison", type="primary", key="sweep_run"):
        rows: list[dict[str, object]] = []
        skipped: list[str] = []
        progress = st.progress(0.0, text="Running...")
        for i, value in enumerate(values):
            try:
                cfg = variant(config, field, value)
            except ValueError:
                skipped.append(f"{value:g}")
                continue
            if cfg.progression_tolerance_s is None and cfg.search_space_size > SWEEP_CAP:
                skipped.append(f"{value:g}")
                continue
            for algorithm in ("uncoordinated", "greedy", "csp"):
                result = cached_run(cfg, algorithm, SWEEP_BUDGET_S, SWEEP_CAP)
                wait, stops = common.per_car(result)
                rows.append(
                    {
                        "value": value,
                        "strategy": ALGORITHM_LABELS[algorithm],
                        "wait_per_car": round(wait, 2),
                        "stops_per_car": round(stops, 2),
                    }
                )
            progress.progress((i + 1) / len(values), text=f"{axis_title}: {value:g}")
        progress.empty()
        st.session_state[SWEEP_KEY] = (factor, pd.DataFrame(rows), skipped)

    stored = st.session_state.get(SWEEP_KEY)
    if not stored or stored[0] != factor:
        st.html(
            ui.empty_state(
                "Nothing run yet",
                f"Press <b>Run comparison</b> to try {len(values)} values of "
                f"“{factor.lower()}”. It takes a few seconds.",
            )
        )
        return
    _, frame, skipped = stored
    if skipped:
        st.html(
            ui.callout(
                f"Skipped {', '.join(skipped)}: with the green-wave rule off, those roads "
                "have too many plans to search here.",
                "warn",
            )
        )
    if frame.empty:
        return
    fig = px.line(
        frame,
        x="value",
        y="wait_per_car",
        color="strategy",
        markers=True,
        color_discrete_map={ALGORITHM_LABELS[k]: v for k, v in ALGORITHM_COLORS.items()},
        category_orders={"strategy": list(ALGORITHM_LABELS.values())},
    )
    style_figure(fig, height=380, margin={"l": 56, "r": 16, "t": 36, "b": 52})
    fig.update_traces(line_width=2.5, marker_size=8, hovertemplate="%{y:.1f} s<extra></extra>")
    fig.update_xaxes(title=axis_title, tickvals=sorted(frame["value"].unique()))
    fig.update_yaxes(title="Waiting per car (s)", rangemode="tozero")
    fig.update_layout(legend_title_text="")
    common.chart(fig, key="sweep_chart")

    wide = frame.pivot(index="value", columns="strategy", values="wait_per_car")
    none, best = ALGORITHM_LABELS["uncoordinated"], ALGORITHM_LABELS["csp"]
    cuts = [(1 - b / a) * 100 for a, b in zip(wide[none], wide[best], strict=True) if a > 0]
    if cuts:
        st.html(
            ui.callout(
                f"Across these values the optimized plan cut average waiting by "
                f"<b>{min(cuts):.0f}% to {max(cuts):.0f}%</b> compared with no coordination.",
                "info",
            )
        )


def render() -> None:
    """Draw the page."""
    bundle = common.current_bundle()
    st.html(
        ui.page_header(
            "Experiments",
            "One road is one example. Here the three strategies are compared across "
            "several roads, to show that the optimizer wins consistently and what makes "
            "the gap bigger or smaller.",
        )
    )
    benchmark_section()
    sweep_section(bundle.config)
