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
from traffic_coordination.config import ScenarioConfig  # noqa: E402
from traffic_coordination.experiments.scenarios import (  # noqa: E402
    RUN_SCENARIOS,
    build_scenario_configs,
)
from traffic_coordination.metrics import (  # noqa: E402
    FEASIBLE_OPTIMAL,
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
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
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

CSS = """
<style>
    h1, h2, h3 { letter-spacing: -0.01em; }
</style>
"""

BUNDLE_KEY = "last_bundle"
BENCHMARK_KEY = "bench_frame"
SWEEP_KEY = "sweep_frame"
SINGLE_RUN_KEY = "single_run"

NO_RUN_MSG = "No run for this scenario yet — open the **Algorithms** tab and press **Run all algorithms**."  # noqa: E501


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
        st.header("Scenario")
        st.caption("Corridor, timing, demand and objective settings (validated).")

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
        st.subheader("Demand")
        st.selectbox(
            "Demand level label", ["low", "medium", "high", "custom"], key="demand_level"
        )
        st.caption("Label only — the two values below define the demand precisely.")
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
        st.subheader("Search & objective")
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
        st.subheader("Run budget")
        st.slider(
            "CSP time budget (s)", min_value=1.0, max_value=300.0, step=1.0, key="csp_budget"
        )
        st.caption("The CSP stops at this wall-clock budget and reports `incomplete` honestly.")
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

        st.divider()
        st.caption(f"traffic-coordination v{__version__}")

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
        return None, f"Invalid scenario configuration: {exc}"


def current_bundle(config: ScenarioConfig) -> RunBundle | None:
    """Return the cached run bundle when it matches the current scenario."""
    bundle = st.session_state.get(BUNDLE_KEY)
    if isinstance(bundle, RunBundle):
        if config_fingerprint(bundle.config) == config_fingerprint(config):
            return bundle
        st.info("The scenario changed since the last run — re-run from the Algorithms tab.")
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


def tab_overview(config: ScenarioConfig | None, error: str | None) -> None:
    """Render the KPI overview tab."""
    st.subheader("Scenario summary")
    if error or config is None:
        st.error(error)
        st.caption("Fix the sidebar inputs; every tab becomes active once the scenario validates.")
        return
    warning = scenario_warning(config)
    if warning:
        st.info(warning)
    bundle = current_bundle(config)
    left, mid, right = st.columns(3)
    with left:
        st.metric("Intersections", config.n_intersections)
        st.metric("Cycle length C", f"{config.cycle_length:.0f} s")
        st.metric("Coordinated green G", f"{config.green_duration:.0f} s")
    with mid:
        st.metric("Offsets per signal |D|", config.offsets_per_intersection)
        st.metric("Raw search space", f"{config.search_space_size:,}")
        st.metric(
            "Vehicles (all directions)",
            len(config.directions) * config.vehicles_per_direction,
        )
    with right:
        st.metric(
            "Progression constraint",
            f"±{config.progression_tolerance_s:.0f} s"
            if config.progression_tolerance_s is not None
            else "disabled",
        )
        st.metric(
            "Objective",
            f"{config.objective_weight_wait:g}·W + {config.objective_weight_stop:g}·S",
        )
        st.metric("Seed", config.seed)

    st.subheader("Last run")
    if bundle is None:
        st.info(NO_RUN_MSG)
    else:
        st.metric("CSP status", bundle.csp.status)
        df = results_dataframe(bundle.results)
        st.dataframe(
            df[["algorithm", "status", "total_waiting_time_s", "total_stops", "objective"]],
            hide_index=True,
            width="stretch",
        )
    st.caption(
        "All numbers are simulated under the documented model (constant speed, "
        "no queues) — they are neither field measurements nor the report's "
        "illustrative figures."
    )


def tab_corridor(config: ScenarioConfig | None, error: str | None) -> None:
    """Render the live corridor diagram and vehicle animation."""
    if error or config is None:
        st.info("Fix the sidebar inputs first.")
        return
    corridor, _ = make_scenario(config)
    bundle = current_bundle(config)
    max_traces = 200

    if bundle is None:
        st.info(
            "Showing the uncoordinated reference plan (all offsets 0). Run an "
            "algorithm to see the optimised plan and live traffic."
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

    time_s = st.slider(
        "View time t (s)",
        0.0,
        float(max(120.0, 3 * config.cycle_length)),
        0.0,
        1.0,
        key="corridor_time",
    )
    st.plotly_chart(
        corridor_figure(corridor, config, offsets, simulation, time_s),
        width="stretch",
    )
    if bundle is not None:
        st.caption(
            "Animation note: with very large demands the first 200 vehicle "
            "traces are drawn; reported metrics always use every vehicle."
        )
        st.plotly_chart(
            vehicle_animation_figure(
                corridor,
                config,
                offsets,
                trimmed_simulation(bundle.csp.simulation, 100),
                frames=48,
            ),
            width="stretch",
        )


def tab_timeline(config: ScenarioConfig | None, error: str | None) -> None:
    """Render the signal-offset timeline."""
    if error or config is None:
        st.info("Fix the sidebar inputs first.")
        return
    bundle = current_bundle(config)
    offsets = tuple(bundle.csp.plan.offsets) if bundle else (0.0,) * config.n_intersections
    horizon = st.slider(
        "Timeline horizon (s)",
        float(config.cycle_length),
        float(8 * config.cycle_length),
        float(4 * config.cycle_length),
        key="timeline_horizon",
    )
    st.plotly_chart(
        signal_timeline_figure(offsets, config, horizon), width="stretch"
    )
    st.caption(
        "Green window of intersection i starts at its offset O_i, lasts G "
        "seconds and repeats every C seconds; coordination shifts each row."
    )
    if bundle is None:
        st.caption("Showing the uncoordinated reference plan (all offsets 0).")
    else:
        st.dataframe(
            pd.DataFrame(
                {
                    "intersection": [f"I{i + 1}" for i in range(config.n_intersections)],
                    "offset_s": list(offsets),
                }
            ),
            hide_index=True,
        )


def tab_algorithms(config: ScenarioConfig | None, error: str | None) -> None:
    """Render the run controls and single-run buttons."""
    if error or config is None:
        st.info("Fix the sidebar inputs first.")
        return
    st.subheader("Run the three coordination strategies")
    st.caption(
        f"All algorithms evaluate the same generated vehicle set "
        f"({len(config.directions) * config.vehicles_per_direction} vehicles) "
        "with the same deterministic simulator."
    )
    run_col, cancel_space = st.columns([1, 2])
    with run_col:
        if st.button("▶ Run all algorithms", type="primary"):
            with st.spinner("Simulating demand and searching the offset space…"):
                bundle = run_all_algorithms(
                    config,
                    time_budget_s=float(st.session_state["csp_budget"]),
                    evaluation_cap=(
                        int(st.session_state["eval_cap"])
                        if st.session_state["cap_enabled"]
                        else None
                    ),
                    verify_exhaustive=bool(st.session_state["verify_flag"]),
                )
            st.session_state[BUNDLE_KEY] = bundle
            st.session_state.pop(SINGLE_RUN_KEY, None)
            st.rerun()

    warning = scenario_warning(config)
    if warning:
        st.info(warning)

    st.divider()
    st.subheader("Single runs (cached per scenario + budget)")
    col1, col2, col3 = st.columns(3)
    budget = float(st.session_state["csp_budget"])
    with col1:
        if st.button("Uncoordinated"):
            st.session_state[SINGLE_RUN_KEY] = cached_run(config, "uncoordinated", budget, None)
    with col2:
        if st.button("Greedy"):
            st.session_state[SINGLE_RUN_KEY] = cached_run(config, "greedy", budget, None)
    with col3:
        if st.button("CSP"):
            st.session_state[SINGLE_RUN_KEY] = cached_run(config, "csp", budget, None)
    single = st.session_state.get(SINGLE_RUN_KEY)
    if isinstance(single, AlgorithmResult):
        status_icon = "✅" if single.status != STATUS_NO_SOLUTION else "⚠️"
        st.write(f"{status_icon} **{single.algorithm}** — {single.status}")
        st.dataframe(results_dataframe([single]), hide_index=True, width="stretch")

    st.divider()
    st.subheader("Benchmark suite")
    st.caption(
        "Re-runs scenarios A–E exactly as the repository's benchmark runner does "
        "(uncoordinated, greedy, CSP + exhaustive verification where the space "
        "allows). This blocks the UI for roughly a minute on a laptop; the CLI "
        "`python -m traffic_coordination.experiments.benchmark_runner --all` is "
        "the recommended way."
    )
    if st.button("Run benchmark scenarios A–E now"):
        with st.spinner("Running benchmark scenarios A–E…"):
            import traffic_coordination.experiments.benchmark_runner as runner

            frame, _meta = runner.run_suite(runner.MAIN_SCENARIOS)
        st.session_state[BENCHMARK_KEY] = frame
    if BENCHMARK_KEY in st.session_state:
        st.dataframe(st.session_state[BENCHMARK_KEY], width="stretch")


def tab_results(config: ScenarioConfig | None, error: str | None) -> None:
    """Render the comparison table, charts, verification and final plan."""
    if error or config is None:
        st.info("Fix the sidebar inputs first.")
        return
    bundle = current_bundle(config)
    if bundle is None:
        st.info(NO_RUN_MSG)
        return
    df = results_dataframe(bundle.results)
    st.subheader("Comparison")
    st.dataframe(df, hide_index=True, width="stretch")

    if bundle.csp.status == STATUS_NO_SOLUTION:
        st.error(
            "The CSP found no feasible plan under the current hard constraints "
            "(try increasing the progression tolerance)."
        )
        return

    base_row = df.loc[df["algorithm"] == "uncoordinated", "objective"]
    if not base_row.empty and float(base_row.iloc[0]) > 0:
        best = float(df["objective"].min())
        base = float(base_row.iloc[0])
        improvement = (base - best) / base * 100
        st.metric("Best objective improvement over uncoordinated", f"{improvement:.1f}%")

    waiting_chart = px.bar(
        df, x="algorithm", y="total_waiting_time_s", color="algorithm",
        title="Total waiting time (s) — lower is better",
    )
    stops_chart = px.bar(
        df, x="algorithm", y="total_stops", color="algorithm",
        title="Total stops — fewer is better",
    )
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.plotly_chart(waiting_chart, width="stretch")
    with chart_right:
        st.plotly_chart(stops_chart, width="stretch")

    if bundle.verification is not None:
        ver = bundle.verification
        if ver.completed and ver.best_offsets is not None:
            agrees = abs(ver.best_objective - bundle.csp.simulation.objective) < 1e-9
            if agrees:
                st.success(
                    f"Independent exhaustive search over {ver.feasible_plans:,} feasible "
                    f"plans confirms the CSP optimum (J = {ver.best_objective:.2f})."
                )
            else:
                st.error(
                    "Independent verification found a better plan than the CSP — this "
                    "would be a correctness bug; please report it."
                )
        else:
            st.warning(
                "Exhaustive verification did not finish within its 60 s budget; "
                "optimality is not verified for this run."
            )
    elif bundle.verification_skipped:
        st.info(f"Optimality verification: {bundle.verification_skipped}.")

    st.subheader("Selected timing plan (CSP)")
    st.dataframe(
        pd.DataFrame(
            {
                "intersection": [f"I{i + 1}" for i in range(config.n_intersections)],
                "offset_s": list(bundle.csp.plan.offsets),
            }
        ),
        hide_index=True,
    )
    if bundle.csp.status != FEASIBLE_OPTIMAL:
        st.caption(
            f"CSP status: {bundle.csp.status} — the plan is best-so-far, not proven optimal."
        )


def tab_search_inspector(config: ScenarioConfig | None, error: str | None) -> None:
    """Render CSP search statistics, trace charts and the event table."""
    if error or config is None:
        st.info("Fix the sidebar inputs first.")
        return
    bundle = current_bundle(config)
    if bundle is None:
        st.info("Run the CSP algorithm first (Algorithms tab).")
        return
    stats = bundle.csp.metadata["search_stats"]
    st.subheader("CSP search statistics")
    st.dataframe(
        pd.DataFrame(
            [(str(k), str(v)) for k, v in stats.items()],
            columns=["statistic", "value"],
        ).set_index("statistic"),
        width="stretch",
    )
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.plotly_chart(
            traceviz.trace_event_summary_figure(bundle.csp_trace), width="stretch"
        )
    with chart_right:
        st.plotly_chart(
            traceviz.trace_depth_figure(bundle.csp_trace), width="stretch"
        )
    st.subheader("Recorded events")
    st.caption(
        "The trace retains the first events of the search up to its cap, in "
        "chronological order; the aggregate counters above cover the entire "
        "search, not just the retained window."
    )
    st.dataframe(
        traceviz.trace_dataframe(bundle.csp_trace), width="stretch", height=420
    )


def tab_sensitivity(config: ScenarioConfig | None, error: str | None) -> None:
    """Render one-dimensional sensitivity sweeps computed live."""
    if error or config is None:
        st.info("Fix the sidebar inputs first.")
        return
    st.subheader("Sensitivity analysis")
    st.caption(
        "Each sweep varies one axis at a time using the other sidebar settings. "
        "Every value is a fresh run of all three algorithms on identical demand."
    )
    axis = st.selectbox(
        "Sweep axis",
        [
            "Traffic demand (vehicles per direction)",
            "Nominal speed (km/h)",
            "Corridor size (intersections)",
            "Offset resolution (s)",
        ],
    )
    quick = st.checkbox("Fast mode (5 s CSP budget, 30,000-plan cap)", value=True)
    options: list[float] = {
        "Traffic demand (vehicles per direction)": [5.0, 10.0, 20.0, 30.0, 50.0],
        "Nominal speed (km/h)": [25.0, 30.0, 40.0, 50.0, 60.0],
        "Corridor size (intersections)": [3.0, 4.0, 5.0, 6.0, 7.0],
        "Offset resolution (s)": [1.0, 2.0, 5.0],
    }[axis]
    default = options[:4] if axis.startswith("Offset") else options
    chosen = st.multiselect("Values", options, default=default)
    if not chosen:
        st.info("Pick at least one value.")
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
        st.session_state[SWEEP_KEY] = pd.DataFrame(rows)

    frame = st.session_state.get(SWEEP_KEY)
    if isinstance(frame, pd.DataFrame) and not frame.empty:
        st.dataframe(frame, hide_index=True, width="stretch")
        fig = px.line(
            frame,
            x=frame["value"].astype(str),
            y="objective",
            color="algorithm",
            markers=True,
            title=f"Objective vs {axis.lower()} "
            f"(J = {config.objective_weight_wait:g}·W + {config.objective_weight_stop:g}·S)",
        )
        fig.update_xaxes(title=axis)
        st.plotly_chart(fig, width="stretch")


def tab_export(config: ScenarioConfig | None, error: str | None) -> None:
    """Render export buttons for the current run's real data."""
    if error or config is None:
        st.info("Fix the sidebar inputs first.")
        return
    st.subheader("Export this session's run data")
    bundle = current_bundle(config)
    if bundle is None:
        st.info("Run a comparison first; exports contain the actual run results.")
        return
    import json

    df = results_dataframe(bundle.results)
    st.download_button(
        "Download comparison results (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        file_name="coordination_results.csv",
        mime="text/csv",
    )
    plans = {
        result.algorithm: {"offsets": list(result.plan.offsets), "status": result.status}
        for result in bundle.results
    }
    st.download_button(
        "Download timing plans (JSON)",
        json.dumps({"config": config.to_dict(), "plans": plans}, indent=2).encode("utf-8"),
        file_name="timing_plans.json",
        mime="application/json",
    )
    st.download_button(
        "Download CSP search trace (JSON)",
        json.dumps(
            {"search_stats": bundle.csp.metadata["search_stats"], **bundle.csp_trace},
            indent=2,
            default=str,
        ).encode("utf-8"),
        file_name="search_trace.json",
        mime="application/json",
    )
    trace_frame = traceviz.trace_dataframe(bundle.csp_trace)
    st.download_button(
        "Download search-trace events (CSV)",
        trace_frame.to_csv(index=False).encode("utf-8"),
        file_name="search_trace.csv",
        mime="text/csv",
    )
    st.caption("Benchmark result files live in `experiments/results/` in the repository.")


def tab_learn() -> None:
    """Render the educational explanations used during the viva."""
    st.header("How this works — viva-ready explanations")
    st.markdown(
        "### 1. State space\n"
        "A *state* is a partial assignment of offsets `(O_1, ..., O_k)`; a complete "
        "state is one timing plan. `O_1 = 0` is fixed as the global time "
        "reference, so the space is `|D|^(N-1)` — e.g. 12^4 = 20,736 plans for "
        "N=5, C=60 s, a 5 s grid."
    )
    st.markdown(
        "### 2. CSP formulation\n"
        "- **Variables:** signal offsets `O_2..O_N`.\n"
        "- **Domains:** the discrete grid `{0, r, 2r, ..., C-r}`.\n"
        "- **Hard constraints:** domain bounds, the fixed reference offset and "
        "(optionally) a progression tolerance between adjacent intersections.\n"
        "- **Soft objective:** `J = α·W + β·S`, evaluated by deterministic simulation."
    )
    st.markdown(
        "### 3. Forward checking\n"
        "After assigning `O_i`, the solver removes values from `O_{i+1}`'s domain "
        "that violate the pairwise constraint. The constraint graph is a chain, so "
        "one future neighbour suffices. With no progression constraint configured, "
        "forward checking removes nothing — stated honestly — and the ablation "
        "(`use_forward_checking=False`) is available in the test suite."
    )
    st.markdown(
        "### 4. Branch and bound\n"
        "The search keeps the best complete plan (the incumbent). A subtree is "
        "pruned only when a *valid lower bound* cannot beat the incumbent. The "
        "implemented bound `h(s) = 0` is admissible and consistent but weak — it "
        "prunes nothing in practice, and the `branch_bound_prunes` counter reports "
        "the real (usually zero) value instead of an inflated figure."
    )
    st.markdown(
        "### 5. Objective function\n"
        "`J = α·W + β·S`: W is total waiting time in seconds and S the stop count. "
        "With the default α=1, β=2, one stop costs like two seconds of delay. "
        "Change the weights in the sidebar to see the trade-off shift."
    )
    st.markdown(
        "### 6. Search-space growth\n"
        "Adding one intersection multiplies the space by |D| (12 on the default "
        "grid) — the curved growth behind the scalability chart in the report."
    )
    st.markdown(
        "### 7. Simulation limitations\n"
        "Constant speed, no acceleration profiles, no queue interactions or "
        "capacity limits, one coordinated green per signal, no pedestrians or "
        "turns. Good for demonstrating classical AI search on a synthetic "
        "arterial; **not** a traffic-engineering design tool."
    )


def main() -> None:
    """Compose the dashboard page."""
    seed_default_state()
    st.markdown(CSS, unsafe_allow_html=True)
    st.title("🚦 Classical AI-Based Traffic Signal Coordination")
    st.caption(
        "ECSCT24301 · Foundation of AI · Adani University — educational "
        "simulation and decision-support prototype. Not a certified "
        "traffic-control system, not field validated."
    )

    config, error = render_sidebar()

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
