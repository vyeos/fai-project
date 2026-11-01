"""Shared state, vocabulary and helpers for the dashboard pages.

The "Try it" page owns the only inputs: a plain-language description of a
road (``road``) that maps onto a :class:`ScenarioConfig`. Every page reads the
latest run for that road, so the explanations on later pages always talk
about the numbers the reader just produced.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from traffic_coordination import ui_theme as ui
from traffic_coordination.config import ScenarioConfig
from traffic_coordination.metrics import (
    FEASIBLE_OPTIMAL,
    FEASIBLE_SINGLE,
    FEASIBLE_SUBOPTIMAL,
    FEASIBLE_TIME_LIMIT,
    STATUS_NO_SOLUTION,
    AlgorithmResult,
)
from traffic_coordination.models import SimulationResult
from traffic_coordination.scenario_generator import make_scenario
from traffic_coordination.signal_timing import travel_time_seconds
from traffic_coordination.simulator import simulate_plan
from traffic_coordination.ui_state import RunBundle, config_fingerprint, run_all_algorithms
from traffic_coordination.visualization import ALGORITHM_LABELS

ROAD_KEY = "road_inputs"
BUNDLE_KEY = "bundle"
RUNS_KEY = "runs"

# Pages register themselves here (from app.py) so any page can link to another.
PAGES: dict[str, Any] = {}

ROAD_DEFAULTS: dict[str, Any] = {
    "lights": 5,
    "distance_m": 400,
    "speed_kmh": 40,
    "traffic": "Moderate",
    "directions": "Both ways",
    "arrivals": "In a bunch",
    "cycle_s": 60,
    "green_s": 30,
    "step_s": 5,
    "tolerance_s": 10,
    "stop_cost": 2.0,
}

# label -> (demand_level, cars per direction, seconds between cars)
TRAFFIC: dict[str, tuple[str, int, float]] = {
    "Light": ("low", 10, 3.0),
    "Moderate": ("medium", 20, 1.0),
    "Heavy": ("high", 50, 1.0),
}
DIRECTIONS = {"Both ways": "both", "One way": "forward"}
ARRIVALS = {"In a bunch": "platoon", "Spread out": "uniform"}

# Solver budgets are fixed for the dashboard; runs stay well under them.
TIME_BUDGET_S = 30.0
EVALUATION_CAP = 250_000

STRATEGY_TEXT = {
    "uncoordinated": (
        "Every light turns green at the same moment. This is the starting point the "
        "other two are measured against."
    ),
    "greedy": (
        "Each light turns green one driving-time after the light before it, so cars "
        "heading up the road ride a green wave. Quick, but it ignores cars going the "
        "other way."
    ),
    "csp": (
        "Tries every allowed combination of start times, skips the ones that cannot "
        "win, and keeps the plan with the lowest score."
    ),
}

STATUS_TEXT = {
    FEASIBLE_OPTIMAL: ("Best possible", "ok"),
    FEASIBLE_TIME_LIMIT: ("Best found in time", "warn"),
    FEASIBLE_SUBOPTIMAL: ("Rule of thumb", "neutral"),
    FEASIBLE_SINGLE: ("Fixed rule", "neutral"),
    STATUS_NO_SOLUTION: ("No valid plan", "bad"),
}


def get_road() -> dict[str, Any]:
    """Return the reader's road description (defaults on first visit)."""
    road = st.session_state.setdefault(ROAD_KEY, dict(ROAD_DEFAULTS))
    for key, value in ROAD_DEFAULTS.items():
        road.setdefault(key, value)
    return road


def road_to_config(road: dict[str, Any]) -> ScenarioConfig:
    """Translate the plain-language road description into a scenario."""
    level, cars, headway = TRAFFIC[road["traffic"]]
    tolerance = float(road["tolerance_s"])
    return ScenarioConfig(
        n_intersections=int(road["lights"]),
        cycle_length=float(road["cycle_s"]),
        green_duration=float(road["green_s"]),
        link_distance_m=float(road["distance_m"]),
        speed_kmh=float(road["speed_kmh"]),
        demand_level=level,
        vehicles_per_direction=cars,
        headway_s=headway,
        departure_pattern=ARRIVALS[road["arrivals"]],
        direction_mode=DIRECTIONS[road["directions"]],
        offset_resolution_s=float(road["step_s"]),
        objective_weight_wait=1.0,
        objective_weight_stop=float(road["stop_cost"]),
        progression_tolerance_s=tolerance if tolerance > 0 else None,
    )


def road_problem(road: dict[str, Any]) -> str | None:
    """Explain, in words, why a road description cannot be simulated."""
    cycle, green, step = road["cycle_s"], road["green_s"], road["step_s"]
    if green > cycle:
        return f"Green time ({green} s) cannot be longer than the whole cycle ({cycle} s)."
    if cycle % step:
        return (
            f"The timing step ({step} s) must divide the cycle ({cycle} s) evenly, so "
            "every start time lands on the same grid. Try a 5 s step."
        )
    if road["tolerance_s"] and road["tolerance_s"] > cycle / 2:
        return f"The green-wave rule can be at most half the cycle (±{cycle / 2:g} s)."
    try:
        road_to_config(road)
    except ValueError as exc:
        return str(exc)
    return None


def run_road(road: dict[str, Any]) -> RunBundle:
    """Run all three strategies for ``road`` (reusing an identical earlier run)."""
    config = road_to_config(road)
    runs: dict[str, RunBundle] = st.session_state.setdefault(RUNS_KEY, {})
    key = config_fingerprint(config)
    if key not in runs:
        runs[key] = run_all_algorithms(
            config,
            time_budget_s=TIME_BUDGET_S,
            evaluation_cap=EVALUATION_CAP,
            verify_exhaustive=True,
        )
    st.session_state[BUNDLE_KEY] = runs[key]
    return runs[key]


def current_bundle() -> RunBundle:
    """Return the latest run, running the default road on a first visit."""
    bundle = st.session_state.get(BUNDLE_KEY)
    if isinstance(bundle, RunBundle):
        return bundle
    with st.spinner("Simulating the default road..."):
        return run_road(get_road())


def link_seconds(config: ScenarioConfig) -> float:
    """Seconds needed to drive from one light to the next at the speed limit."""
    return travel_time_seconds(config.link_distance_m, config.speed_kmh)


def per_car(result: AlgorithmResult) -> tuple[float, float]:
    """Average waiting seconds and stops per car for one strategy."""
    sim = result.simulation
    n = max(sim.n_vehicles, 1)
    return sim.total_waiting_time / n, sim.total_stops / n


def drop(before: float, after: float) -> str:
    """'-85%' style change label; empty when the baseline is zero."""
    if before <= 0:
        return ""
    return f"{(after - before) / before * 100:+.0f}%"


def status_label(result: AlgorithmResult) -> tuple[str, str]:
    """Plain status word and badge tone for a strategy result."""
    return STATUS_TEXT.get(result.status, (result.status, "neutral"))


def traced(bundle: RunBundle, algorithm: str) -> SimulationResult:
    """Simulate one strategy's plan with per-car traces for drawing."""
    result = {"uncoordinated": bundle.uncoordinated, "greedy": bundle.greedy, "csp": bundle.csp}[
        algorithm
    ]
    if result.simulation.vehicle_traces:
        return result.simulation
    _, vehicles = make_scenario(bundle.config)
    return simulate_plan(result.plan, vehicles, bundle.config, collect_traces=True)


def strategy_cards(bundle: RunBundle) -> str:
    """Render the three strategies as cards, in fixed order."""
    cards = []
    for result in bundle.results:
        wait, stops = per_car(result)
        label, tone = status_label(result)
        cards.append(
            ui.StrategyCard(
                algorithm=result.algorithm,
                name=ALGORITHM_LABELS[result.algorithm],
                description=STRATEGY_TEXT[result.algorithm],
                status=label,
                tone=tone,
                wait_per_car=wait,
                stops_per_car=stops,
                score=result.simulation.objective,
            )
        )
    return ui.strategy_cards(cards)


def road_sentence(config: ScenarioConfig) -> str:
    """One sentence describing the simulated road and traffic."""
    cars = len(config.directions) * config.vehicles_per_direction
    ways = "in both directions" if config.direction_mode == "both" else "in one direction"
    return (
        f"{config.n_intersections} lights, {config.link_distance_m:g} m apart, "
        f"{config.speed_kmh:g} km/h speed limit, {cars} cars driving {ways}."
    )


def chart(fig: Any, key: str | None = None) -> None:
    """Render a Plotly figure with the dashboard theme (not Streamlit's)."""
    st.plotly_chart(
        fig,
        width="stretch",
        theme=None,
        key=key,
        config={"displaylogo": False, "displayModeBar": False},
    )


def link_to(page: str, label: str) -> None:
    """Link to another registered page."""
    if page in PAGES:
        st.page_link(PAGES[page], label=label, icon=":material/arrow_forward:")
