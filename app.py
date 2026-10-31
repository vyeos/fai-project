"""Streamlit dashboard for classical AI-based traffic signal coordination.

Run from the repository root:

    python -m streamlit run app.py

The app mirrors the demonstration flow: overview KPIs, corridor and timeline
visualisation, algorithm runs, comparison results, CSP search-trace
inspection, sensitivity sweeps, data export, and educational explanations.

Honesty note (displayed in the app): all metrics come from the deterministic
simplified simulator documented in the report; nothing here is a field
measurement and the app does not control real signals.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

# Allow running from a source checkout without an editable install.
_SRC = Path(__file__).resolve().parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from traffic_coordination import __version__  # noqa: E402
from traffic_coordination import ui_theme as ui  # noqa: E402
from traffic_coordination.config import ScenarioConfig  # noqa: E402
from traffic_coordination.experiments.scenarios import (  # noqa: E402
    RUN_SCENARIOS,
    build_scenario_configs,
)
from traffic_coordination.metrics import (  # noqa: E402
    FEASIBLE_OPTIMAL,
    FEASIBLE_SINGLE,
    FEASIBLE_SUBOPTIMAL,
    FEASIBLE_TIME_LIMIT,
    STATUS_NO_SOLUTION,
    AlgorithmResult,
    results_dataframe,
)
from traffic_coordination.models import SimulationResult, timing_plan  # noqa: E402
from traffic_coordination.scenario_generator import make_scenario  # noqa: E402
from traffic_coordination.ui_state import (  # noqa: E402
    RunBundle,
    cached_run,
    config_fingerprint,
    run_all_algorithms,
)
from traffic_coordination.visualization import (  # noqa: E402
    ALGORITHM_COLORS,
    style_figure,
)
from traffic_coordination.visualization import search_trace as traceviz  # noqa: E402
from traffic_coordination.visualization.corridor import corridor_figure  # noqa: E402
from traffic_coordination.visualization.timeline import (  # noqa: E402
    signal_timeline_figure,
)
from traffic_coordination.visualization.vehicle_animation import (  # noqa: E402
    vehicle_animation_figure,
)

st.set_page_config(
    page_title="Traffic Signal Coordination — Classical AI",
    page_icon=":material/traffic:",
    layout="wide",
    initial_sidebar_state="auto",
)

DEFAULTS: dict[str, Any] = {
    "n_intersections": 5,
    "cycle_length": 60.0,
    "green_duration": 30.0,
    "link_distance_m": 400.0,
    "speed_kmh": 40.0,
    "demand_level": "medium",
    "vehicles_per_direction": 20,
    "headway_s": 1.0,
    "departure_pattern": "platoon",
    "direction_mode": "both",
    "seed": 42,
    "offset_resolution": 5.0,
    "alpha": 1.0,
    "beta": 2.0,
    "tol_enabled": True,
    "progression_tolerance": 10.0,
    "csp_budget": 30.0,
    "cap_enabled": True,
    "eval_cap": 250_000,
    "verify_flag": True,
}

BUNDLE_KEY = "last_bundle"
BENCHMARK_KEY = "bench_frame"
SWEEP_KEY = "sweep_frame"
SINGLE_RUN_KEY = "single_run"

NO_RUN_TITLE = "No run for this scenario yet"
NO_RUN_BODY = (
    "Press <b>Run all algorithms</b> on the Overview or Algorithms tab. All three "
    "strategies are evaluated on the same generated vehicles."
)

STATUS_LABELS = {
    FEASIBLE_OPTIMAL: ("proven optimal", "ok"),
    FEASIBLE_TIME_LIMIT: ("incomplete", "warn"),
    FEASIBLE_SUBOPTIMAL: ("heuristic", "neutral"),
    FEASIBLE_SINGLE: ("fixed plan", "neutral"),
    STATUS_NO_SOLUTION: ("no feasible plan", "bad"),
}


def seed_default_state() -> None:
    """Seed widget keys with defaults on first visit (preserved afterwards)."""
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, value)


def apply_preset(name: str) -> None:
    """Push a registered benchmark scenario's values into the widget keys."""
    config = build_scenario_configs()[name]
    mapping = {
        "n_intersections": config.n_intersections,
        "cycle_length": config.cycle_length,
        "green_duration": config.green_duration,
        "link_distance_m": config.link_distance_m,
        "speed_kmh": config.speed_kmh,
        "demand_level": config.demand_level,
        "vehicles_per_direction": config.vehicles_per_direction,
        "headway_s": config.headway_s,
        "departure_pattern": config.departure_pattern,
        "direction_mode": config.direction_mode,
        "seed": config.seed,
        "offset_resolution": config.offset_resolution_s,
        "alpha": config.objective_weight_wait,
        "beta": config.objective_weight_stop,
        "tol_enabled": config.progression_tolerance_s is not None,
        "progression_tolerance": (
            config.progression_tolerance_s
            if config.progression_tolerance_s is not None
            else 10.0
        ),
    }
    for key, value in mapping.items():
        st.session_state[key] = value


def render_sidebar() -> tuple[ScenarioConfig | None, str | None]:
    """Render sidebar controls and return the validated config or an error."""
    with st.sidebar:
        st.subheader("Scenario", anchor=False)

        preset = st.selectbox(
            "Load benchmark scenario",
            ["(custom)"] + list(RUN_SCENARIOS),
            format_func=lambda name: (
                name if name == "(custom)" else f"{name} — {RUN_SCENARIOS[name]['description']}"
            ),
        )
        col_load, col_reset = st.columns(2)
        with col_load:
            if st.button("Load", disabled=preset == "(custom)"):
                apply_preset(preset)
                st.session_state["loaded_preset"] = preset
                st.rerun()
        with col_reset:
            if st.button("Defaults"):
                for key, value in DEFAULTS.items():
                    st.session_state[key] = value
                st.rerun()

        st.number_input("Intersections (N)", min_value=2, max_value=10, key="n_intersections")
        st.number_input(
            "Cycle length C (s)", min_value=30.0, max_value=180.0, step=5.0, key="cycle_length"
        )
        st.number_input(
            "Coordinated green G (s)",
            min_value=5.0,
            max_value=180.0,
            step=5.0,
            key="green_duration",
            help="Must satisfy 0 < G <= C.",
        )
        st.number_input(
            "Link distance (m)",
            min_value=50.0,
            max_value=3000.0,
            step=50.0,
            key="link_distance_m",
        )
        st.number_input(
            "Nominal speed (km/h)",
            min_value=10.0,
            max_value=100.0,
            step=5.0,
            key="speed_kmh",
        )

        st.divider()
        st.subheader("Demand", anchor=False)
        st.selectbox(
            "Demand level label", ["low", "medium", "high", "custom"], key="demand_level"
        )
        st.caption("Label only. The two values below define the demand.")
        st.slider(
            "Vehicles per direction",
            min_value=2,
            max_value=150,
            step=1,
            key="vehicles_per_direction",
        )
        st.slider(
            "Departure headway (s)",
            min_value=0.5,
            max_value=10.0,
            step=0.5,
            key="headway_s",
        )
        st.selectbox("Departure pattern", ["platoon", "uniform"], key="departure_pattern")
        st.selectbox("Directions", ["both", "forward", "reverse"], key="direction_mode")

        st.divider()
        st.subheader("Search & objective", anchor=False)
        st.select_slider(
            "Offset resolution (s)", options=[1.0, 2.0, 5.0, 10.0], key="offset_resolution"
        )
        st.checkbox(
            "Enable hard progression constraint",
            key="tol_enabled",
            help="Restricted pairwise offset constraint; without it the raw space "
            "is D^(N-1) plans, which is expensive for large N.",
        )
        st.slider(
            "Progression tolerance (s)",
            min_value=1.0,
            max_value=30.0,
            step=1.0,
            key="progression_tolerance",
            disabled=not st.session_state["tol_enabled"],
            help="Maximum circular deviation between adjacent offset differences "
            "and the nominal link travel time.",
        )
        alpha_col, beta_col = st.columns(2)
        with alpha_col:
            st.number_input(
                "alpha (wait weight)", min_value=0.0, max_value=10.0, step=0.5, key="alpha"
            )
        with beta_col:
            st.number_input(
                "beta (stop weight)", min_value=0.0, max_value=10.0, step=0.5, key="beta"
            )
        st.number_input(
            "Random seed (arrival jitter)",
            min_value=0,
            max_value=10_000,
            step=1,
            key="seed",
        )

        st.divider()
        st.subheader("Run budget", anchor=False)
        st.slider(
            "CSP time budget (s)", min_value=1.0, max_value=300.0, step=1.0, key="csp_budget"
        )
        st.caption("At this wall-clock budget the CSP stops and reports `incomplete`.")
        st.checkbox("Cap simulated complete plans", key="cap_enabled")
        st.slider(
            "Evaluation cap",
            min_value=1_000,
            max_value=2_000_000,
            step=10_000,
            key="eval_cap",
            disabled=not st.session_state["cap_enabled"],
        )
        st.checkbox(
            "Verify CSP optimality by exhaustive search (small spaces)", key="verify_flag"
        )


    state = st.session_state
    config_dict: dict[str, Any] = {
        "n_intersections": int(state["n_intersections"]),
        "cycle_length": float(state["cycle_length"]),
        "green_duration": float(state["green_duration"]),
        "link_distance_m": float(state["link_distance_m"]),
        "speed_kmh": float(state["speed_kmh"]),
        "demand_level": state["demand_level"],
        "vehicles_per_direction": int(state["vehicles_per_direction"]),
        "headway_s": float(state["headway_s"]),
        "departure_pattern": state["departure_pattern"],
        "direction_mode": state["direction_mode"],
        "seed": int(state["seed"]),
        "jitter_s": 0.0,
        "offset_resolution_s": float(state["offset_resolution"]),
        "objective_weight_wait": float(state["alpha"]),
        "objective_weight_stop": float(state["beta"]),
        "progression_tolerance_s": (
            float(state["progression_tolerance"]) if state["tol_enabled"] else None
        ),
    }
    try:
        return ScenarioConfig(**config_dict), None
    except ValueError as exc:
        return None, str(exc)


def current_bundle_quiet(config: ScenarioConfig | None) -> RunBundle | None:
    """Return the cached run bundle when it matches ``config``, without notices."""
    bundle = st.session_state.get(BUNDLE_KEY)
    if config is not None and isinstance(bundle, RunBundle):
        if config_fingerprint(bundle.config) == config_fingerprint(config):
            return bundle
    return None


def current_bundle(config: ScenarioConfig) -> RunBundle | None:
    """Return the cached run bundle when it matches the current scenario."""
    bundle = st.session_state.get(BUNDLE_KEY)
    if isinstance(bundle, RunBundle):
        if config_fingerprint(bundle.config) == config_fingerprint(config):
            return bundle
        st.info("The scenario changed since the last run. Run the comparison again to refresh.")
    return None


def scenario_warning(config: ScenarioConfig) -> str | None:
    """Non-blocking advisory about potentially expensive configurations."""
    if config.progression_tolerance_s is None and config.search_space_size > 100_000:
        budget = st.session_state.get("csp_budget", 30.0)
        return (
            f"With no progression constraint the raw space is "
            f"**{config.search_space_size:,}** offset combinations. The CSP uses "
            f"the {budget:.0f} s budget and the evaluation cap and will report "
            "`incomplete` honestly if the space is too big. Enabling the "
            "progression tolerance lets forward checking prune the search."
        )
    return None


def trimmed_simulation(simulation: SimulationResult, max_traces: int) -> SimulationResult:
    """Copy a simulation result with at most ``max_traces`` vehicle traces."""
    traces = simulation.vehicle_traces
    if len(traces) <= max_traces:
        return simulation
    return replace(simulation, vehicle_traces=traces[:max_traces])


def status_label(status: str) -> tuple[str, str]:
    """Short label and tone for an algorithm status string."""
    return STATUS_LABELS.get(status, (status, "neutral"))


def chart(fig: Any) -> None:
    """Render a Plotly figure with the dashboard theme (not Streamlit's)."""
    st.plotly_chart(
        fig, width="stretch", theme=None, config={"displaylogo": False, "displayModeBar": False}
    )


def ledger_html(results: list[AlgorithmResult]) -> str:
    """Comparison ledger for a list of algorithm results."""
    rows = []
    for result in sorted(
        results, key=lambda r: ("uncoordinated", "greedy", "csp").index(r.algorithm)
    ):
        label, tone = status_label(result.status)
        rows.append(
            ui.LedgerRow(
                algorithm=result.algorithm,
                status=label,
                tone=tone,
                waiting_s=result.simulation.total_waiting_time,
                stops=result.simulation.total_stops,
                objective=result.simulation.objective,
            )
        )
    return ui.ledger(rows)


def run_comparison(config: ScenarioConfig) -> None:
    """Run all three algorithms on ``config`` and store the bundle."""
    with st.spinner("Simulating demand and searching the offset space..."):
        bundle = run_all_algorithms(
            config,
            time_budget_s=float(st.session_state["csp_budget"]),
            evaluation_cap=(
                int(st.session_state["eval_cap"]) if st.session_state["cap_enabled"] else None
            ),
            verify_exhaustive=bool(st.session_state["verify_flag"]),
        )
    st.session_state[BUNDLE_KEY] = bundle
    st.session_state.pop(SINGLE_RUN_KEY, None)
    st.rerun()


def need_valid_config() -> None:
    """Shared notice for tabs that cannot render without a valid scenario."""
    st.html(
        ui.empty_state(
            "The scenario is not valid",
            "Fix the highlighted sidebar inputs; every tab comes back once it validates.",
        )
    )


def tab_overview(config: ScenarioConfig | None, error: str | None) -> None:
    """Render the scenario overview and the latest comparison."""
    if error or config is None:
        st.error(error)
        need_valid_config()
        return
    warning = scenario_warning(config)
    if warning:
        st.warning(warning)
    bundle = current_bundle(config)

    travel_s = config.link_distance_m / (config.speed_kmh / 3.6)
    domain = config.offsets_per_intersection
    hero = ui.hero_stat(
        "Raw search space",
        f"{config.search_space_size:,}",
        "plans",
        f"<code>|D|^(N-1) = {domain}^{config.n_intersections - 1}</code> offset "
        f"combinations, with O<sub>1</sub> = 0 fixed as the time reference. "
        f"A vehicle at nominal speed needs about {travel_s:.0f} s per link.",
    )
    tolerance = (
        f"±{config.progression_tolerance_s:g} s"
        if config.progression_tolerance_s is not None
        else "off"
    )
    spec = ui.spec_sheet(
        [
            ("Intersections", f"{config.n_intersections}"),
            ("Offsets per signal", f"{domain}"),
            ("Cycle C", f"{config.cycle_length:g} s"),
            ("Green G", f"{config.green_duration:g} s"),
            ("Link distance", f"{config.link_distance_m:g} m"),
            ("Nominal speed", f"{config.speed_kmh:g} km/h"),
            ("Vehicles", f"{len(config.directions) * config.vehicles_per_direction}"),
            ("Progression", tolerance),
            (
                "Objective",
                f"{config.objective_weight_wait:g}·W + {config.objective_weight_stop:g}·S",
            ),
            ("Seed", f"{config.seed}"),
        ]
    )
    st.html(ui.overview_block(hero, spec))

    if bundle is None:
        st.html(ui.section_title("Last run", "01"))
        st.html(ui.empty_state(NO_RUN_TITLE, NO_RUN_BODY))
        if st.button("Run all algorithms", type="primary", key="overview_run"):
            run_comparison(config)
    else:
        label, _tone = status_label(bundle.csp.status)
        st.html(ui.section_title("Last run", "01", f"CSP {label}"))
        st.html(ledger_html(bundle.results))
    st.html(
        ui.footer(
            "Simulated under the documented model: constant speed, no queues",
            f"traffic-coordination v{__version__}",
        )
    )


def tab_corridor(config: ScenarioConfig | None, error: str | None) -> None:
    """Render the live corridor diagram and vehicle animation."""
    if error or config is None:
        need_valid_config()
        return
    corridor, _ = make_scenario(config)
    bundle = current_bundle(config)
    max_traces = 200

    if bundle is None:
        st.html(
            ui.callout(
                "Showing the <b>uncoordinated reference plan</b> (all offsets 0). Run the "
                "comparison to see the optimised plan with live traffic.",
            )
        )
        empty = SimulationResult(
            plan=timing_plan([0.0] * config.n_intersections),
            total_waiting_time=0.0,
            average_waiting_time=0.0,
            total_stops=0,
            n_vehicles=0,
            objective=0.0,
        )
        simulation = empty
        offsets = (0.0,) * config.n_intersections
    else:
        simulation = trimmed_simulation(bundle.csp.simulation, max_traces)
        offsets = tuple(bundle.csp.plan.offsets)

    st.html(ui.section_title("Corridor snapshot", "01", "Scrub time to move the vehicles"))
    time_s = st.slider(
        "View time t (s)",
        0.0,
        float(max(120.0, 3 * config.cycle_length)),
        0.0,
        1.0,
        key="corridor_time",
    )
    chart(corridor_figure(corridor, config, offsets, simulation, time_s))
    if bundle is not None:
        st.html(
            ui.section_title(
                "Vehicle replay", "02", "Steel = forward, amber = reverse; first 100 vehicles"
            )
        )
        chart(
            vehicle_animation_figure(
                corridor,
                config,
                offsets,
                trimmed_simulation(bundle.csp.simulation, 100),
                frames=48,
            )
        )
        st.caption(
            "With very large demand only the first 200 vehicle traces are drawn; "
            "reported metrics always use every vehicle."
        )


def tab_timeline(config: ScenarioConfig | None, error: str | None) -> None:
    """Render the signal-offset timeline."""
    if error or config is None:
        need_valid_config()
        return
    bundle = current_bundle(config)
    offsets = tuple(bundle.csp.plan.offsets) if bundle else (0.0,) * config.n_intersections
    plan = "CSP plan" if bundle else "Uncoordinated reference plan"
    st.html(ui.section_title("Signal timeline", "01", plan))
    st.html(ui.offset_strip(offsets))
    horizon = st.slider(
        "Timeline horizon (s)",
        float(config.cycle_length),
        float(8 * config.cycle_length),
        float(4 * config.cycle_length),
        key="timeline_horizon",
    )
    chart(signal_timeline_figure(offsets, config, horizon))
    st.caption(
        "The green window of intersection i starts at its offset O_i, lasts G seconds "
        "and repeats every C seconds. Coordination shifts each row."
    )


def tab_algorithms(config: ScenarioConfig | None, error: str | None) -> None:
    """Render the run controls and single-run buttons."""
    if error or config is None:
        need_valid_config()
        return
    vehicles = len(config.directions) * config.vehicles_per_direction
    st.html(
        ui.section_title(
            "Run the comparison", "01", f"Same {vehicles} vehicles, same deterministic simulator"
        )
    )
    if st.button("Run all algorithms", type="primary", key="algorithms_run"):
        run_comparison(config)

    warning = scenario_warning(config)
    if warning:
        st.warning(warning)

    st.html(ui.section_title("Single runs", "02", "Cached per scenario and budget"))
    col1, col2, col3, _spacer = st.columns([1, 1, 1, 3])
    budget = float(st.session_state["csp_budget"])
    with col1:
        if st.button("Uncoordinated", width="stretch"):
            st.session_state[SINGLE_RUN_KEY] = cached_run(config, "uncoordinated", budget, None)
    with col2:
        if st.button("Greedy", width="stretch"):
            st.session_state[SINGLE_RUN_KEY] = cached_run(config, "greedy", budget, None)
    with col3:
        if st.button("CSP", width="stretch"):
            st.session_state[SINGLE_RUN_KEY] = cached_run(config, "csp", budget, None)
    single = st.session_state.get(SINGLE_RUN_KEY)
    if isinstance(single, AlgorithmResult):
        st.html(ledger_html([single]))
        with st.expander("All counters for this run"):
            st.dataframe(results_dataframe([single]), hide_index=True, width="stretch")

    st.html(ui.section_title("Benchmark suite", "03", "Scenarios A to E"))
    st.html(
        ui.callout(
            "Re-runs scenarios A to E exactly as the repository's benchmark runner does, "
            "including exhaustive verification where the space allows. It blocks the page "
            "for about a minute; the CLI <code>python -m "
            "traffic_coordination.experiments.benchmark_runner --all</code> is the "
            "recommended route."
        )
    )
    if st.button("Run benchmark scenarios A to E"):
        with st.spinner("Running benchmark scenarios A to E..."):
            import traffic_coordination.experiments.benchmark_runner as runner

            frame, _meta = runner.run_suite(runner.MAIN_SCENARIOS)
        st.session_state[BENCHMARK_KEY] = frame
    if BENCHMARK_KEY in st.session_state:
        st.dataframe(st.session_state[BENCHMARK_KEY], width="stretch")


def verification_html(bundle: RunBundle) -> str:
    """Statement about the independent exhaustive check of the CSP optimum."""
    ver = bundle.verification
    if ver is not None:
        if ver.completed and ver.best_offsets is not None:
            if abs(ver.best_objective - bundle.csp.simulation.objective) < 1e-9:
                return ui.callout(
                    f"<b>Verified.</b> An independent exhaustive search over "
                    f"{ver.feasible_plans:,} feasible plans finds the same optimum, "
                    f"J = {ver.best_objective:,.2f}.",
                    "ok",
                )
            return ui.callout(
                "<b>Verification disagrees.</b> The exhaustive search found a better plan "
                "than the CSP. That would be a correctness bug; please report it.",
                "bad",
            )
        return ui.callout(
            "<b>Not verified.</b> The exhaustive check did not finish within its 60 s "
            "budget, so optimality is unconfirmed for this run.",
            "warn",
        )
    if bundle.verification_skipped:
        return ui.callout(f"<b>Verification skipped:</b> {bundle.verification_skipped}.")
    return ui.callout("Exhaustive verification was switched off for this run.")


def tab_results(config: ScenarioConfig | None, error: str | None) -> None:
    """Render the comparison headline, charts, verification and final plan."""
    if error or config is None:
        need_valid_config()
        return
    bundle = current_bundle(config)
    if bundle is None:
        st.html(ui.empty_state(NO_RUN_TITLE, NO_RUN_BODY))
        return
    df = results_dataframe(bundle.results)

    if bundle.csp.status == STATUS_NO_SOLUTION:
        st.html(
            ui.callout(
                "<b>No feasible plan.</b> The CSP found no plan under the current hard "
                "constraints. Try a wider progression tolerance.",
                "bad",
            )
        )
        st.dataframe(df, hide_index=True, width="stretch")
        return

    base = bundle.uncoordinated.simulation.objective
    best = min(r.simulation.objective for r in bundle.results)
    if base > 0:
        left = ui.hero_stat(
            "Objective reduction vs uncoordinated",
            f"{(base - best) / base * 100:.1f}",
            "%",
            f"J falls from {base:,.0f} to {best:,.0f}.",
        )
    else:
        left = ui.hero_stat("Best objective", f"{best:,.0f}", "J", "Uncoordinated J is zero.")
    st.html(ui.headline_block(left, verification_html(bundle)))

    st.html(ui.section_title("Comparison", "01"))
    st.html(ledger_html(bundle.results))

    waiting_chart = px.bar(
        df,
        x="algorithm",
        y="total_waiting_time_s",
        color="algorithm",
        color_discrete_map=ALGORITHM_COLORS,
    )
    stops_chart = px.bar(
        df, x="algorithm", y="total_stops", color="algorithm", color_discrete_map=ALGORITHM_COLORS
    )
    for fig, title, y_title in (
        (waiting_chart, "Total waiting time", "seconds"),
        (stops_chart, "Total stops", "stops"),
    ):
        style_figure(fig, title=title, showlegend=False, height=340, bargap=0.45)
        fig.update_traces(marker_line_width=0)
        fig.update_xaxes(title=None)
        fig.update_yaxes(title=y_title)
    chart_left, chart_right = st.columns(2, gap="large")
    with chart_left:
        chart(waiting_chart)
    with chart_right:
        chart(stops_chart)

    st.html(ui.section_title("Selected timing plan", "02", "CSP offsets per intersection"))
    st.html(ui.offset_strip(bundle.csp.plan.offsets))
    if bundle.csp.status != FEASIBLE_OPTIMAL:
        st.caption(
            f"CSP status: {bundle.csp.status}. This plan is the best found so far, "
            "not a proven optimum."
        )
    with st.expander("Full comparison table"):
        st.dataframe(df, hide_index=True, width="stretch")


def tab_search_inspector(config: ScenarioConfig | None, error: str | None) -> None:
    """Render CSP search statistics, trace charts and the event table."""
    if error or config is None:
        need_valid_config()
        return
    bundle = current_bundle(config)
    if bundle is None:
        st.html(
            ui.empty_state(
                "Nothing to inspect yet",
                "Run the comparison first. The inspector shows the CSP's counters and "
                "the recorded window of its search trace.",
            )
        )
        return
    stats = bundle.csp.metadata["search_stats"]

    def fmt(value: object) -> str:
        if isinstance(value, bool):
            return "yes" if value else "no"
        if isinstance(value, int):
            return f"{value:,}"
        if isinstance(value, float):
            return f"{value:,.4g}"
        return str(value)

    st.html(ui.section_title("Search statistics", "01", "Counters cover the whole search"))
    st.html(ui.kv_grid([(str(k).replace("_", " "), fmt(v)) for k, v in stats.items()]))
    chart_left, chart_right = st.columns(2, gap="large")
    with chart_left:
        chart(traceviz.trace_event_summary_figure(bundle.csp_trace))
    with chart_right:
        chart(traceviz.trace_depth_figure(bundle.csp_trace))
    st.html(
        ui.section_title(
            "Recorded events", "02", "The first events up to the trace cap, in order"
        )
    )
    st.dataframe(traceviz.trace_dataframe(bundle.csp_trace), width="stretch", height=420)


def tab_sensitivity(config: ScenarioConfig | None, error: str | None) -> None:
    """Render one-dimensional sensitivity sweeps computed live."""
    if error or config is None:
        need_valid_config()
        return
    st.html(
        ui.section_title(
            "Sensitivity sweep",
            "01",
            "One axis at a time; each value reruns all three algorithms",
        )
    )
    axis_col, values_col = st.columns([1, 2], gap="large")
    with axis_col:
        axis = st.selectbox(
            "Sweep axis",
            [
                "Traffic demand (vehicles per direction)",
                "Nominal speed (km/h)",
                "Corridor size (intersections)",
                "Offset resolution (s)",
            ],
        )
    options: list[float] = {
        "Traffic demand (vehicles per direction)": [5.0, 10.0, 20.0, 30.0, 50.0],
        "Nominal speed (km/h)": [25.0, 30.0, 40.0, 50.0, 60.0],
        "Corridor size (intersections)": [3.0, 4.0, 5.0, 6.0, 7.0],
        "Offset resolution (s)": [1.0, 2.0, 5.0],
    }[axis]
    default = options[:4] if axis.startswith("Offset") else options
    with values_col:
        chosen = st.multiselect("Values", options, default=default)
    quick = st.checkbox("Fast mode (5 s CSP budget, 30,000-plan cap)", value=True)
    if not chosen:
        st.html(ui.empty_state("No values selected", "Pick at least one value to sweep."))
        return
    if st.button("Run sweep", type="primary"):
        budget = 5.0 if quick else float(st.session_state["csp_budget"])
        cap = 30_000 if quick else int(st.session_state["eval_cap"])
        rows: list[dict[str, object]] = []
        progress = st.progress(0.0)
        for idx, value in enumerate(chosen):
            variant = ScenarioConfig(
                n_intersections=(
                    int(value) if axis.startswith("Corridor") else config.n_intersections
                ),
                cycle_length=config.cycle_length,
                green_duration=config.green_duration,
                link_distance_m=config.link_distance_m,
                speed_kmh=value if axis.startswith("Nominal") else config.speed_kmh,
                demand_level="custom",
                vehicles_per_direction=(
                    int(value) if axis.startswith("Traffic") else config.vehicles_per_direction
                ),
                headway_s=config.headway_s,
                departure_pattern=config.departure_pattern,
                direction_mode=config.direction_mode,
                seed=config.seed,
                offset_resolution_s=(
                    value if axis.startswith("Offset") else config.offset_resolution_s
                ),
                objective_weight_wait=config.objective_weight_wait,
                objective_weight_stop=config.objective_weight_stop,
                progression_tolerance_s=config.progression_tolerance_s,
            )
            space = variant.search_space_size
            if space > cap:
                st.warning(
                    f"Skipping value {value:g}: raw space {space:,} exceeds the "
                    f"{cap:,}-plan cap. Enable the progression tolerance (or raise "
                    "the cap) to sweep this value."
                )
                continue
            for algorithm in ("uncoordinated", "greedy", "csp"):
                result = cached_run(variant, algorithm, budget, cap)
                rows.append(
                    {
                        "value": value,
                        "algorithm": algorithm,
                        "waiting_s": round(result.simulation.total_waiting_time, 1),
                        "stops": result.simulation.total_stops,
                        "objective": round(result.simulation.objective, 1),
                        "status": (
                            "proven optimal" if result.status == FEASIBLE_OPTIMAL else result.status
                        ),
                        "plans_simulated": result.complete_assignments_evaluated,
                    }
                )
            progress.progress((idx + 1) / len(chosen))
        progress.empty()
        st.session_state[SWEEP_KEY] = pd.DataFrame(rows)

    frame = st.session_state.get(SWEEP_KEY)
    if isinstance(frame, pd.DataFrame) and not frame.empty:
        fig = px.line(
            frame,
            x=frame["value"].astype(str),
            y="objective",
            color="algorithm",
            markers=True,
            color_discrete_map=ALGORITHM_COLORS,
        )
        style_figure(
            fig,
            title=f"Objective J = {config.objective_weight_wait:g}·W + "
            f"{config.objective_weight_stop:g}·S",
            height=400,
        )
        fig.update_traces(line_width=2, marker_size=7)
        fig.update_xaxes(title=axis)
        fig.update_layout(legend_title_text="")
        chart(fig)
        with st.expander("Sweep data"):
            st.dataframe(frame, hide_index=True, width="stretch")


def tab_export(config: ScenarioConfig | None, error: str | None) -> None:
    """Render export buttons for the current run's real data."""
    if error or config is None:
        need_valid_config()
        return
    st.html(ui.section_title("Export this session's run", "01", "Files hold the actual results"))
    bundle = current_bundle(config)
    if bundle is None:
        st.html(
            ui.empty_state(
                "Nothing to export yet",
                "Run the comparison first; every download contains that run's real data.",
            )
        )
        return
    import json

    df = results_dataframe(bundle.results)
    plans = {
        result.algorithm: {"offsets": list(result.plan.offsets), "status": result.status}
        for result in bundle.results
    }
    trace_frame = traceviz.trace_dataframe(bundle.csp_trace)
    downloads = [
        (
            "Comparison results",
            "CSV",
            df.to_csv(index=False).encode("utf-8"),
            "coordination_results.csv",
            "text/csv",
        ),
        (
            "Timing plans",
            "JSON",
            json.dumps({"config": config.to_dict(), "plans": plans}, indent=2).encode("utf-8"),
            "timing_plans.json",
            "application/json",
        ),
        (
            "CSP search trace",
            "JSON",
            json.dumps(
                {"search_stats": bundle.csp.metadata["search_stats"], **bundle.csp_trace},
                indent=2,
                default=str,
            ).encode("utf-8"),
            "search_trace.json",
            "application/json",
        ),
        (
            "Search-trace events",
            "CSV",
            trace_frame.to_csv(index=False).encode("utf-8"),
            "search_trace.csv",
            "text/csv",
        ),
    ]
    columns = st.columns(2, gap="medium")
    for i, (label, kind, data, name, mime) in enumerate(downloads):
        with columns[i % 2]:
            st.download_button(
                f"{label} · {kind}", data, file_name=name, mime=mime, width="stretch"
            )
    st.caption("Benchmark result files live in `experiments/results/` in the repository.")


LEARN_SECTIONS: list[tuple[str, str]] = [
    (
        "State space",
        "<p>A <em>state</em> is a partial assignment of offsets <code>(O_1, ..., O_k)</code>; "
        "a complete state is one timing plan. <code>O_1 = 0</code> is fixed as the global "
        "time reference, so the space is <code>|D|^(N-1)</code>, e.g. 12<sup>4</sup> = "
        "20,736 plans for N = 5, C = 60 s and a 5 s grid.</p>",
    ),
    (
        "CSP formulation",
        "<ul><li><b>Variables:</b> signal offsets <code>O_2..O_N</code>.</li>"
        "<li><b>Domains:</b> the discrete grid <code>{0, r, 2r, ..., C-r}</code>.</li>"
        "<li><b>Hard constraints:</b> domain bounds, the fixed reference offset and, "
        "optionally, a progression tolerance between adjacent intersections.</li>"
        "<li><b>Soft objective:</b> <code>J = α·W + β·S</code>, evaluated by deterministic "
        "simulation.</li></ul>",
    ),
    (
        "Forward checking",
        "<p>After assigning <code>O_i</code>, the solver removes values from "
        "<code>O_{i+1}</code>'s domain that violate the pairwise constraint. The constraint "
        "graph is a chain, so one future neighbour is enough. With no progression constraint "
        "forward checking removes nothing, and the dashboard says so; the ablation "
        "(<code>use_forward_checking=False</code>) lives in the test suite.</p>",
    ),
    (
        "Branch and bound",
        "<p>The search keeps the best complete plan found so far (the incumbent). A subtree "
        "is pruned only when a <em>valid lower bound</em> cannot beat it. The implemented "
        "bound <code>h(s) = 0</code> is admissible and consistent but weak: it prunes "
        "nothing in practice, and the <code>branch_bound_prunes</code> counter reports the "
        "real, usually zero, value.</p>",
    ),
    (
        "Objective function",
        "<p><code>J = α·W + β·S</code>, where W is total waiting time in seconds and S the "
        "number of stops. With the default α = 1 and β = 2, one stop costs as much as two "
        "seconds of delay. Change the weights in the sidebar to move the trade-off.</p>",
    ),
    (
        "Search-space growth",
        "<p>Each extra intersection multiplies the space by |D|, which is 12 on the default "
        "grid. That is the curve behind the scalability chart in the report.</p>",
    ),
    (
        "Simulation limits",
        "<p>Constant speed, no acceleration profiles, no queue interactions or capacity "
        "limits, one coordinated green per signal, no pedestrians or turns. It is good for "
        "demonstrating classical AI search on a synthetic arterial and is <b>not</b> a "
        "traffic-engineering design tool.</p>",
    ),
]


def tab_learn() -> None:
    """Render the educational explanations used during the viva."""
    st.html(ui.section_title("How it works", None, "Seven ideas behind the dashboard"))
    st.html(ui.prose_sections(LEARN_SECTIONS))


def main() -> None:
    """Compose the dashboard page."""
    seed_default_state()
    st.markdown(ui.GLOBAL_CSS, unsafe_allow_html=True)

    config, error = render_sidebar()

    eyebrow = "ECSCT24301 · Foundation of AI · Adani University"
    bundle = current_bundle_quiet(config)
    if config is None:
        st.html(ui.masthead(None, 0.0, 0.0, "", eyebrow))
    else:
        offsets = (
            tuple(bundle.csp.plan.offsets) if bundle else (0.0,) * config.n_intersections
        )
        st.html(
            ui.masthead(
                offsets,
                config.cycle_length,
                config.green_duration,
                "CSP plan" if bundle else "Reference plan",
                eyebrow,
            )
        )

    overview, corridor, timeline, algorithms, results, inspector, sensitivity, export, learn = (
        st.tabs(
            [
                "Overview",
                "Corridor",
                "Signals",
                "Algorithms",
                "Results",
                "Search inspector",
                "Sensitivity",
                "Export",
                "Learn",
            ]
        )
    )
    with overview:
        tab_overview(config, error)
    with corridor:
        tab_corridor(config, error)
    with timeline:
        tab_timeline(config, error)
    with algorithms:
        tab_algorithms(config, error)
    with results:
        tab_results(config, error)
    with inspector:
        tab_search_inspector(config, error)
    with sensitivity:
        tab_sensitivity(config, error)
    with export:
        tab_export(config, error)
    with learn:
        tab_learn()


if __name__ == "__main__":
    main()
