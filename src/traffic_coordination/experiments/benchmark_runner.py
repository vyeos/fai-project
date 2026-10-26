"""Benchmark runner: executes scenarios, saves results, metadata and summary.

Run from the repository root:

    python -m traffic_coordination.experiments.benchmark_runner --all
    python -m traffic_coordination.experiments.benchmark_runner --scenario B

Outputs (under ``experiments/``):

- ``results/benchmark_results.csv`` — one row per (scenario, algorithm).
- ``results/benchmark_metadata.json`` — full configuration, seeds, git commit,
  library versions, verification outcomes.
- ``results/summary.md`` — human-readable tables and notes.

Methodological rules enforced here:

- every algorithm sees the *same* generated vehicle set for a scenario;
- scenarios use stored seeds (all 42) and no hidden randomness;
- exhaustive verification runs when its budget allows (A, B, D, F, G, H, J) and
  is skipped / recorded honestly when the space is too large (C, E);
- timings come from ``time.perf_counter`` (monotonic, high resolution).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd
from matplotlib.figure import Figure  # noqa: F401 (used by reporting)

from traffic_coordination import __version__
from traffic_coordination.algorithms import run_csp, run_greedy, run_uncoordinated
from traffic_coordination.config import ScenarioConfig
from traffic_coordination.scenario_generator import generate_vehicles
from traffic_coordination.verification import exhaustive_best

from .reporting import build_figures, render_summary
from .scenarios import RUN_SCENARIOS, build_scenario_configs, write_configuration_files

RESULTS_DIR = Path("experiments/results")
FIGURES_DIR = Path("experiments/figures")

# Wall-clock budget for exhaustive verification per scenario (seconds).
EXHAUSTIVE_BUDGET_S = 120.0

MAIN_SCENARIOS = ["A", "B", "C", "D", "E"]
SENSITIVITY_SCENARIOS = ["F1", "F2", "F3", "G1", "G2", "H1", "H2", "J1", "J2"]

# Search-space sizes too big for honest, useful exhaustive verification
# (>250k candidate plans → skip and record the decision).
EXHAUSTIVE_SKIP = {"C", "E"}


def run_single(
    name: str, config: ScenarioConfig
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Run all algorithms + verification for one scenario.

    Returns:
        A tuple ``(rows, metadata)`` where ``rows`` are flat per-algorithm
        records for the CSV and ``metadata`` documents the run.

    """
    scenario_doc = RUN_SCENARIOS[name]
    vehicles = generate_vehicles(config)

    runs = {
        "uncoordinated": run_uncoordinated(vehicles, config),
        "greedy": run_greedy(vehicles, config),
        "csp": run_csp(vehicles, config, collect_trace=False),
    }

    if name in EXHAUSTIVE_SKIP:
        verification = {
            "performed": False,
            "reason": "search space too large for exhaustive verification; skipped honestly",
            "space_size": config.offsets_per_intersection ** (config.n_intersections - 1),
        }
    else:
        brute = exhaustive_best(config, vehicles, time_budget_s=EXHAUSTIVE_BUDGET_S)
        csp_obj = runs["csp"].simulation.objective
        matches = (
            brute.completed
            and brute.best_offsets is not None
            and (
                abs(
                    (
                        brute.best_objective
                        if brute.best_objective == brute.best_objective
                        else float("nan")
                    )
                    - csp_obj
                )
                < 1e-9
            )
        )
        verification = {
            "performed": True,
            "completed": brute.completed,
            "feasible_plans": brute.feasible_plans,
            "plans_considered": brute.plans_considered,
            "best_objective": brute.best_objective,
            "csp_matches_brute_force": bool(matches),
        }

    rows: list[dict[str, object]] = []
    for algorithm in ("uncoordinated", "greedy", "csp"):
        result = runs[algorithm]
        row: dict[str, object] = {
            "scenario": name,
            "scenario_description": scenario_doc["description"],
            **result.summary_dict,
            "plan_offsets": list(result.plan.offsets),
        }
        # Final simulated performance of the return plan (for CSP this is the
        # same simulation already accounted inside search_time_s).
        row["alpha"] = config.objective_weight_wait
        row["beta"] = config.objective_weight_stop
        row["seed"] = config.seed
        row["n_intersections"] = config.n_intersections
        row["cycle_length_s"] = config.cycle_length
        row["green_duration_s"] = config.green_duration
        row["offset_resolution_s"] = config.offset_resolution_s
        row["progression_tolerance_s"] = config.progression_tolerance_s
        row["demand_level"] = config.demand_level
        row["vehicles_per_direction"] = config.vehicles_per_direction
        row["headway_s"] = config.headway_s
        row["speed_kmh"] = config.speed_kmh
        row["search_space_size"] = config.search_space_size
        row["exhaustive_completed"] = verification.get("completed", False)
        row["csp_matches_brute_force"] = verification.get("csp_matches_brute_force", False)
        rows.append(row)

    metadata = {
        "scenario": name,
        "description": scenario_doc["description"],
        "config": config.to_dict(),
        "vehicles_generated": len(vehicles),
        "first_arrivals_forward": [v.departure_time for v in vehicles if v.direction == "forward"][
            :5
        ],
        "verification": verification,
        "algorithm_search_times_s": {k: round(v.search_time_s, 4) for k, v in runs.items()},
    }
    return rows, metadata


def run_suite(scenarios: list[str]) -> tuple[pd.DataFrame, dict[str, object]]:
    """Run a suite of scenarios and return (results frame, metadata)."""
    all_rows: list[dict[str, object]] = []
    all_meta: dict[str, object] = {
        "project": "Classical AI-Based Traffic Signal Coordination",
        "version": __version__,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "note": "Simulation results under documented simplifying assumptions; not field data.",
        "exhaustive_budget_s": EXHAUSTIVE_BUDGET_S,
        "scenarios": {},
    }
    for name in scenarios:
        config = build_scenario_configs()[name]
        rows, meta = run_single(name, config)
        all_rows.extend(rows)
        all_meta["scenarios"][name] = meta  # type: ignore[index]
        stopped = (
            not meta["verification"].get("completed", True)
            if meta["verification"].get("performed", True)
            else True
        )
        state = "completed" if not stopped else "skipped or budget-limited"
        print(f"scenario {name}: {len(rows)} algorithm rows; exhaustive={state}")
    return pd.DataFrame(all_rows), all_meta


def save_results(frame: pd.DataFrame, metadata: dict[str, object]) -> tuple[Path, Path, Path]:
    """Persist results CSV, metadata JSON and summary; generate the figures.

    Returns the three written file paths.
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_csv = RESULTS_DIR / "benchmark_results.csv"
    metadata_json = RESULTS_DIR / "benchmark_metadata.json"
    summary_md = RESULTS_DIR / "summary.md"

    frame.to_csv(results_csv, index=False)
    metadata_json.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    summary_md.write_text(render_summary(frame, metadata), encoding="utf-8")
    build_figures(frame, FIGURES_DIR)
    return results_csv, metadata_json, summary_md


def main() -> int:  # noqa: C901, PLR0912
    """CLI entry point: select scenarios, run them, and save all outputs."""
    parser = argparse.ArgumentParser(description="Run reproducible benchmark experiments.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--all", action="store_true", help="run main scenarios A-E plus sensitivity runs"
    )
    target.add_argument("--main", action="store_true", help="run only main scenarios A-E")
    target.add_argument("--sensitivity", action="store_true", help="run only sensitivity scenarios")
    target.add_argument("--scenario", type=str, help="run a single scenario by name")
    args = parser.parse_args()

    if args.all:
        selected = MAIN_SCENARIOS + SENSITIVITY_SCENARIOS
    elif args.main:
        selected = MAIN_SCENARIOS
    elif args.sensitivity:
        selected = SENSITIVITY_SCENARIOS
    else:
        selected = [args.scenario]
        if not all(s in RUN_SCENARIOS for s in selected):
            print(f"unknown scenario: {args.scenario}", file=sys.stderr)
            return 2

    write_configuration_files()
    frame, metadata = run_suite(selected)
    csv_path, json_path, md_path = save_results(frame, metadata)
    print("saved:", csv_path)
    print("saved:", json_path)
    print("saved:", md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
