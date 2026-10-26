"""Registry of reproducible benchmark scenario configurations.

The five main scenarios (A-E) follow the benchmark matrix proposed in the
submitted report (Section 7.3):

+----------+---------------+--------+-------------------+----------------------+
| Scenario | Intersections | Demand | Offset resolution | Extra hard constraint|
+==========+===============+========+===================+======================+
| A        | 3             | low    | 5 s               | none                 |
| B        | 5             | medium | 5 s               | none                 |
| C        | 7             | medium | 5 s               | progression tol 10 s |
| D        | 5             | high   | 5 s               | none                 |
| E        | 5             | medium | 1 s               | progression tol 10 s |
+----------+---------------+--------+-------------------+----------------------+

Rationale for the progression tolerance on C and E: with a *vacuous* constraint
the CSP must simulate every one of D^(N-1) plans (about 2.99M for scenario C,
12.96M for scenario E at 1 s resolution), which is far beyond a sensible
compute budget. The tolerance is an explicit hard constraint: the optimizer
then returns the optimum *within the constrained space*, and this is stated in
every result file.

Sensitivity scenarios (F..) re-run the corridor at N=5 for the medium demand
axis and for the 5 s / 1 s resolution axis under a *matched* constraint, so the
resolution comparison is not confounded by the search space size.

Demand presets: low = 10 vehicles/direction @ 3 s; medium = 20 @ 1 s;
high = 50 @ 1 s. All scenarios use seed 42.
"""

from __future__ import annotations

import json
from pathlib import Path

from traffic_coordination.config import DEMAND_PRESETS, ScenarioConfig

__all__ = [
    "RUN_SCENARIOS",
    "CONFIGURATION_DIR",
    "write_configuration_files",
    "build_scenario_configs",
]


CONFIGURATION_DIR = Path("experiments/configurations")


def _demand(level: str) -> dict[str, float]:
    return DEMAND_PRESETS[level]


def build_scenario_configs() -> dict[str, ScenarioConfig]:
    """Build the in-memory benchmark scenario configurations."""
    low, medium, high = _demand("low"), _demand("medium"), _demand("high")
    return {
        "A": ScenarioConfig(
            n_intersections=3,
            vehicles_per_direction=int(low["vehicles_per_direction"]),
            headway_s=low["headway_s"],
            demand_level="low",
        ),
        "B": ScenarioConfig(
            n_intersections=5,
            vehicles_per_direction=int(medium["vehicles_per_direction"]),
            headway_s=medium["headway_s"],
            demand_level="medium",
        ),
        "C": ScenarioConfig(
            n_intersections=7,
            vehicles_per_direction=int(medium["vehicles_per_direction"]),
            headway_s=medium["headway_s"],
            demand_level="medium",
            progression_tolerance_s=10.0,
        ),
        "D": ScenarioConfig(
            n_intersections=5,
            vehicles_per_direction=int(high["vehicles_per_direction"]),
            headway_s=high["headway_s"],
            demand_level="high",
        ),
        "E": ScenarioConfig(
            n_intersections=5,
            vehicles_per_direction=int(medium["vehicles_per_direction"]),
            headway_s=medium["headway_s"],
            demand_level="medium",
            offset_resolution_s=1.0,
            progression_tolerance_s=10.0,
        ),
        # -- sensitivity axis: demand level at fixed size (N = 5) -------------
        "F1": ScenarioConfig(
            demand_level="low",
            vehicles_per_direction=int(low["vehicles_per_direction"]),
            headway_s=low["headway_s"],
        ),
        "F2": ScenarioConfig(demand_level="medium"),
        "F3": ScenarioConfig(
            demand_level="high",
            vehicles_per_direction=int(high["vehicles_per_direction"]),
            headway_s=high["headway_s"],
        ),
        # -- sensitivity axis: offset resolution at matched constraint (N=5) --
        "G1": ScenarioConfig(demand_level="medium", progression_tolerance_s=10.0),
        "G2": ScenarioConfig(
            demand_level="medium",
            offset_resolution_s=1.0,
            progression_tolerance_s=10.0,
        ),
        # -- sensitivity axis: nominal speed (N = 5, medium demand) -----------
        "H1": ScenarioConfig(demand_level="medium", speed_kmh=30.0),
        "H2": ScenarioConfig(demand_level="medium", speed_kmh=50.0),
        # -- sensitivity axis: objective weights (N = 5, medium demand) -------
        "J1": ScenarioConfig(
            demand_level="medium", objective_weight_wait=1.0, objective_weight_stop=0.0
        ),
        "J2": ScenarioConfig(
            demand_level="medium", objective_weight_wait=1.0, objective_weight_stop=4.0
        ),
    }


def write_configuration_files(directory: Path = CONFIGURATION_DIR) -> list[Path]:
    """Persist every scenario configuration as JSON for reproducibility."""
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, config in build_scenario_configs().items():
        data = {"name": name, "description": RUN_SCENARIOS[name]["description"], **config.to_dict()}
        path = directory / f"scenario_{name}.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        written.append(path)
    return written


RUN_SCENARIOS: dict[str, dict[str, object]] = {
    "A": {
        "description": "3 intersections, low demand, 5 s offsets, no progression constraint",
    },
    "B": {
        "description": "5 intersections, medium demand, 5 s offsets, no progression constraint",
    },
    "C": {
        "description": "7 intersections, medium demand, 5 s offsets, 10 s progression "
        "tolerance (hard constraint active for tractability)",
    },
    "D": {
        "description": "5 intersections, high demand, 5 s offsets, no progression constraint",
    },
    "E": {
        "description": "5 intersections, medium demand, 1 s offsets, 10 s progression "
        "tolerance (hard constraint active for tractability)",
    },
    "F1": {"description": "Sensitivity: 5 intersections, low demand"},
    "F2": {"description": "Sensitivity: 5 intersections, medium demand"},
    "F3": {"description": "Sensitivity: 5 intersections, high demand"},
    "G1": {"description": "Sensitivity: 5 intersections, 5 s offsets, 10 s tolerance"},
    "G2": {"description": "Sensitivity: 5 intersections, 1 s offsets, 10 s tolerance"},
    "H1": {"description": "Sensitivity: 5 intersections, 30 km/h"},
    "H2": {"description": "Sensitivity: 5 intersections, 50 km/h"},
    "J1": {"description": "Sensitivity: objective weights alpha=1, beta=0"},
    "J2": {"description": "Sensitivity: objective weights alpha=1, beta=4"},
}


def config_from_file(path: Path) -> ScenarioConfig:
    return ScenarioConfig.from_dict(json.loads(path.read_text(encoding="utf-8")))
