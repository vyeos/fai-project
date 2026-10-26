"""Reproducible corridor and traffic demand generation.

The generator produces two artefacts from a :class:`ScenarioConfig`:

- a :class:`~traffic_coordination.models.Corridor` with equally or individually
  spaced intersections, and
- a list of :class:`~traffic_coordination.models.VehicleSpec` representing the
  released traffic. Departures follow a platoon or uniform pattern, optionally
  with seeded uniform jitter so results remain exactly reproducible.

Demand presets (documented in the report): *low* = 10 vehicles/direction at a
3 s headway, *medium* = 20 vehicles/direction at 1 s (matches the report's
illustrative benchmark), *high* = 50 vehicles/direction at 1 s.
"""

from __future__ import annotations

import random

from .config import DEMAND_PRESETS, ScenarioConfig
from .models import Corridor, Intersection, VehicleSpec

__all__ = ["DEMAND_PRESETS", "build_corridor", "generate_vehicles", "make_scenario"]


def build_corridor(config: ScenarioConfig) -> Corridor:
    """Build the corridor: N intersections, cumulatively positioned, N-1 links."""
    distances = config.effective_link_distances_m
    positions = [0.0]
    for d in distances:
        positions.append(positions[-1] + d)
    intersections = tuple(
        Intersection(index=i, name=f"I{i + 1}", position_m=p)
        for i, p in enumerate(positions)
    )
    return Corridor(intersections=intersections, link_distances_m=tuple(distances))


def generate_vehicles(config: ScenarioConfig) -> list[VehicleSpec]:
    """Generate the vehicle demand described by ``config``.

    Departure pattern semantics:
      - ``platoon``: vehicles released as one batch, ``headway_s`` apart,
        starting at ``departure_start_s`` in every enabled direction.
      - ``uniform``: the same number of departures are spread evenly across a
        horizon of at least one full cycle length, i.e. ``horizon =
        max(cycle_length, n * headway_s)``, giving a constant flow with spacing
        ``horizon / n``. "Headway" therefore acts as a *minimum* spacing: any
        platoon denser than one cycle is kept at its own spacing.

    With ``jitter_s > 0`` a seeded uniform ``[-jitter, +jitter]`` perturbation is
    applied to every departure time, then clamped to be non-negative. The seed
    is taken from ``config.seed`` so the result is exactly reproducible.
    """
    if config.departure_pattern not in ("platoon", "uniform"):
        raise ValueError(f"Unknown departure pattern {config.departure_pattern!r}")

    rng = random.Random(config.seed)
    n = config.vehicles_per_direction
    direction_offsets = {"forward": 0, "reverse": n}  # id offsets to keep ids unique

    vehicles: list[VehicleSpec] = []
    for direction_name in config.directions:
        base = direction_offsets.get(direction_name, 0)
        if config.departure_pattern == "platoon":
            times = [config.departure_start_s + k * config.headway_s for k in range(n)]
        else:  # uniform: evenly spread over >= one full cycle length
            horizon = max(config.cycle_length, n * config.headway_s)
            spacing = horizon / n
            times = [config.departure_start_s + k * spacing for k in range(n)]
        for k, t in enumerate(times):
            if config.jitter_s > 0:
                jitter = rng.uniform(-config.jitter_s, config.jitter_s)
                t = max(0.0, t + jitter)
            vehicles.append(
                VehicleSpec(vehicle_id=base + k, direction=direction_name, departure_time=t)
            )
    return vehicles


def make_scenario(config: ScenarioConfig) -> tuple[Corridor, list[VehicleSpec]]:
    """Build the corridor and the vehicle demand together."""
    return build_corridor(config), generate_vehicles(config)
