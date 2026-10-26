"""Simulation run state for the Streamlit dashboard.

The dashboard holds scenario widgets in Streamlit's own widget state and keeps
actual *run results* in ``st.session_state`` under these keys. Two runs are
only compared when their scenarios are identical, so the app computes a
config fingerprint that includes the vehicle generation parameters.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import streamlit as st

from traffic_coordination.algorithms import run_csp, run_greedy, run_uncoordinated
from traffic_coordination.config import ScenarioConfig
from traffic_coordination.metrics import AlgorithmResult
from traffic_coordination.scenario_generator import make_scenario
from traffic_coordination.verification import ExhaustiveResult, exhaustive_best

RESULTS_KEY = "run_cache"


@dataclass
class RunBundle:
    """All results for one 'Run all algorithms' action on one scenario."""

    config: ScenarioConfig
    uncoordinated: AlgorithmResult
    greedy: AlgorithmResult
    csp: AlgorithmResult
    csp_trace: dict[str, Any]
    verification: ExhaustiveResult | None
    verification_skipped: str | None

    @property
    def results(self) -> list[AlgorithmResult]:
        """The three algorithm results in fixed display order."""
        return [self.uncoordinated, self.greedy, self.csp]


def config_fingerprint(config: ScenarioConfig) -> str:
    """Stable short fingerprint of the scenario + seed (for run cache keys)."""
    payload = json.dumps(config.to_dict(), sort_keys=True)
    digest = hashlib.sha256(payload.encode()).hexdigest()[:12]
    return digest


def build_scenario_from_widgets(widgets: dict[str, Any]) -> ScenarioConfig:
    """Construct a validated ScenarioConfig from dashboard widget values."""
    return ScenarioConfig(
        n_intersections=int(widgets["n_intersections"]),
        cycle_length=float(widgets["cycle_length"]),
        green_duration=float(widgets["green_duration"]),
        link_distance_m=float(widgets["link_distance_m"]),
        speed_kmh=float(widgets["speed_kmh"]),
        demand_level=widgets["demand_level"],
        vehicles_per_direction=int(widgets["vehicles_per_direction"]),
        headway_s=float(widgets["headway_s"]),
        departure_pattern=widgets["departure_pattern"],
        direction_mode=widgets["direction_mode"],
        departure_start_s=float(widgets["departure_start_s"]),
        jitter_s=float(widgets["jitter_s"]),
        seed=int(widgets["seed"]),
        offset_resolution_s=float(widgets["offset_resolution"]),
        objective_weight_wait=float(widgets["alpha"]),
        objective_weight_stop=float(widgets["beta"]),
        progression_tolerance_s=widgets["progression_tolerance"],
    )


def run_all_algorithms(
    config: ScenarioConfig,
    *,
    time_budget_s: float,
    evaluation_cap: int | None,
    verify_exhaustive: bool,
) -> RunBundle:
    """Run the three algorithms on identical demand and optionally verify."""
    _, vehicles = make_scenario(config)

    uncoordinated_result = run_uncoordinated(vehicles, config)
    greedy_result = run_greedy(vehicles, config)
    csp_result = run_csp(
        vehicles,
        config,
        time_budget_s=time_budget_s,
        evaluation_cap=evaluation_cap,
        collect_trace=True,
        trace_event_limit=1500,
    )

    verification = None
    skipped: str | None = None
    if verify_exhaustive:
        space = config.search_space_size
        if space > 250_000:
            skipped = (
                f"search space is {space:,} plans; exhaustive verification skipped "
                "to keep the dashboard responsive"
            )
        else:
            verification = exhaustive_best(config, vehicles, time_budget_s=60.0)
    else:
        skipped = "verification disabled for this run"
    trace = csp_result.metadata.get("trace") or {"events": [], "truncated": False}
    return RunBundle(
        config=config,
        uncoordinated=uncoordinated_result,
        greedy=greedy_result,
        csp=csp_result,
        csp_trace=trace,
        verification=verification,
        verification_skipped=skipped,
    )


def run_single_algorithm(
    algorithm: str, config: ScenarioConfig, *, time_budget_s: float, evaluation_cap: int | None
) -> AlgorithmResult:
    """Run one algorithm ('uncoordinated' | 'greedy' | 'csp')."""
    _, vehicles = make_scenario(config)
    if algorithm == "uncoordinated":
        return run_uncoordinated(vehicles, config)
    if algorithm == "greedy":
        return run_greedy(vehicles, config)
    if algorithm == "csp":
        return run_csp(
            vehicles,
            config,
            time_budget_s=time_budget_s,
            evaluation_cap=evaluation_cap,
            collect_trace=True,
            trace_event_limit=1500,
        )
    raise ValueError(f"Unknown algorithm {algorithm!r}")


def cache_key(config: ScenarioConfig, algorithm: str, budget: float, cap: int | None) -> str:
    """Build the session-cache key for one algorithm run of one scenario."""
    cap_part = "unlimited" if cap is None else str(cap)
    return "/".join(
        (config_fingerprint(config), algorithm, str(round(budget, 3)), cap_part)
    )


def cached_run(
    config: ScenarioConfig, algorithm: str, budget: float, cap: int | None
) -> AlgorithmResult:
    """Run (or reuse from session cache) a single algorithm run."""
    key = cache_key(config, algorithm, budget, cap)
    state = st.session_state.setdefault(RESULTS_KEY, {})
    if key not in state:
        state[key] = run_single_algorithm(
            algorithm, config, time_budget_s=budget, evaluation_cap=cap
        )
    return state[key]
