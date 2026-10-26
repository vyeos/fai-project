"""Domain models for the traffic signal coordination project.

Containers defined here describe the corridor (intersections, links), the
signal timing plan, and the vehicles that move through the corridor. Pure
geometry/timing arithmetic lives in :mod:`traffic_coordination.signal_timing`;
scenario configuration and validation lives in
:mod:`traffic_coordination.config`.

Units: distances in metres, times in seconds, speeds in km/h.
"""

from __future__ import annotations

import math
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Literal

from .signal_timing import travel_time_seconds

Direction = Literal["forward", "reverse"]

DIRECTION_LABELS: dict[Direction, str] = {
    "forward": "Forward (left-to-right on the corridor)",
    "reverse": "Reverse (right-to-left on the corridor)",
}


@dataclass(frozen=True)
class Intersection:
    """A signalized intersection on the corridor.

    Attributes:
        index: Position in corridor order (0-based, used as CSP variable index).
        name: Human-readable identifier, e.g. ``"I1"``.
        position_m: Signed position along the corridor axis in metres. Intersections
            are ordered so that ``position`` strictly increases with ``index``.

    """

    index: int
    name: str
    position_m: float

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError(f"Intersection index must be non-negative, got {self.index}")
        if not math.isfinite(self.position_m):
            raise ValueError(f"Intersection position must be finite, got {self.position_m}")


@dataclass(frozen=True)
class Corridor:
    """A linear arterial corridor of signalized intersections.

    The corridor stores ``N`` intersections in corridor order plus the ``N - 1``
    link distances between consecutive intersections (link ``i`` connects
    intersection ``i`` and ``i + 1``).

    Note: link distances apply to both directions of travel; the simplified model
    assumes a single nominal speed shared by all vehicles.
    """

    intersections: tuple[Intersection, ...]
    link_distances_m: tuple[float, ...]

    def __post_init__(self) -> None:
        n = len(self.intersections)
        if n < 2:
            raise ValueError(f"A corridor needs at least 2 intersections, got {n}")
        if len(self.link_distances_m) != n - 1:
            raise ValueError(
                f"Corridor with {n} intersections needs {n - 1} link distances, "
                f"got {len(self.link_distances_m)}"
            )
        if any(d <= 0 for d in self.link_distances_m):
            raise ValueError("All link distances must be positive")
        positions = [it.position_m for it in self.intersections]
        if any(b - a <= 0 for a, b in zip(positions, positions[1:], strict=True)):
            raise ValueError("Intersection positions must strictly increase along the corridor")

    @property
    def n_intersections(self) -> int:
        """Number of signalized intersections N on the corridor."""
        return len(self.intersections)

    @property
    def total_length_m(self) -> float:
        """Total corridor length in metres (sum of link distances)."""
        return sum(self.link_distances_m)

    def link_indices_for_direction(self, direction: Direction) -> tuple[int, ...]:
        """Return the intersection indices a vehicle visits for ``direction``.

        Forward vehicles visit intersections ``0, 1, ..., N-1``; reverse vehicles
        visit ``N-1, N-2, ..., 0``. In both cases the vehicle traverses the same
        links, so link travel times are shared between directions.
        """
        if direction == "forward":
            return tuple(range(self.n_intersections))
        return tuple(range(self.n_intersections - 1, -1, -1))

    def travel_time_between(
        self, i: int, j: int, speed_kmh: float
    ) -> float:
        """Return travel time in seconds between adjacent intersections.

        ``i`` and ``j`` must be adjacent indices in corridor order; the link
        between position ``min(i, j)`` and ``max(i, j)`` is used for both
        directions.
        """
        if abs(i - j) != 1:
            raise ValueError(f"Intersections {i} and {j} are not adjacent")
        return travel_time_seconds(self.link_distances_m[min(i, j)], speed_kmh)

    def __iter__(self) -> Iterator[Intersection]:
        return iter(self.intersections)


@dataclass(frozen=True)
class TimingPlan:
    """A complete signal timing plan: the ordered vector of offsets ``[O_1..O_N]``.

    The first offset is the temporal reference and is fixed to 0 (validated), as
    specified in the project report. Global shifts of a plan produce equivalent
    outcomes, so the search fixes ``O_1 = 0`` and plans the rest.
    """

    offsets: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.offsets) < 2:
            raise ValueError(f"A timing plan needs at least 2 offsets, got {len(self.offsets)}")
        if any(not math.isfinite(o) for o in self.offsets):
            raise ValueError("Offsets must be finite numbers")
        if self.offsets[0] != 0.0:
            raise ValueError(
                "The first offset O_1 is the global reference and must be 0 "
                f"(got {self.offsets[0]}); globally shifted plans are equivalent"
            )
        if any(o < 0 for o in self.offsets):
            raise ValueError(f"Offsets must be non-negative, got {self.offsets}")

    def __len__(self) -> int:
        return len(self.offsets)

    def __iter__(self) -> Iterator[float]:
        return iter(self.offsets)

    def __getitem__(self, i: int) -> float:
        return self.offsets[i]


@dataclass(frozen=True)
class VehicleSpec:
    """A vehicle request entering the corridor.

    ``departure_time`` is the time the vehicle would arrive at its *first*
    signal if it did not wait, i.e. the departure time already includes the
    (fixed) travel from an upstream source onto the corridor. It becomes the
    first arrival time in :meth:`simulator.simulate_plan`.
    """

    vehicle_id: int
    direction: Direction
    departure_time: float

    def __post_init__(self) -> None:
        if self.vehicle_id < 0:
            raise ValueError(f"vehicle_id must be non-negative, got {self.vehicle_id}")
        if self.direction not in ("forward", "reverse"):
            raise ValueError(f"direction must be 'forward' or 'reverse', got {self.direction!r}")
        if self.departure_time < 0:
            raise ValueError(
                f"departure_time must be non-negative, got {self.departure_time}"
            )


@dataclass
class VehicleTrace:
    """Per-vehicle simulation trace for visualizations and detailed analysis."""

    vehicle_id: int
    direction: Direction
    arrival_at_intersection: dict[int, float] = field(default_factory=dict)
    wait_at_intersection: dict[int, float] = field(default_factory=dict)
    departure_from_intersection: dict[int, float] = field(default_factory=dict)
    total_wait: float = 0.0
    stops: int = 0


@dataclass
class SimulationResult:
    """Outcome of simulating one timing plan over a fixed vehicle set.

    All aggregates are summed over **both** directions of travel.
    """

    plan: TimingPlan
    total_waiting_time: float
    average_waiting_time: float
    total_stops: int
    n_vehicles: int
    objective: float
    vehicle_traces: list[VehicleTrace] = field(default_factory=list)
    per_intersections: dict[int, dict[str, float]] = field(default_factory=dict)

    @property
    def waiting_time_by_intersection(self) -> dict[int, float]:
        """Total simulated waiting time per intersection index (seconds)."""
        return {i: stats.get("waiting_time", 0.0) for i, stats in self.per_intersections.items()}

    def summary_dict(self) -> dict[str, float | int]:
        """Return a flat dictionary of headline metrics for tables and exports."""
        return {
            "total_waiting_time_s": round(self.total_waiting_time, 6),
            "average_waiting_time_s": round(self.average_waiting_time, 6),
            "total_stops": self.total_stops,
            "objective": round(self.objective, 6),
            "n_vehicles": self.n_vehicles,
        }


def timing_plan(offsets: Sequence[float]) -> TimingPlan:
    """Construct a timing plan from any ordered sequence of offsets."""
    return TimingPlan(tuple(float(o) for o in offsets))
