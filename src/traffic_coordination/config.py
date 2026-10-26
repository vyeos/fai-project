"""Scenario configuration with validation for the coordination project.

A :class:`ScenarioConfig` captures every parameter needed to build a corridor,
generate vehicle demand, define the discrete offset domain, and weight the
objective function. It is deliberately a plain, serialisable dataclass so that a
benchmark configuration can be written to JSON and reproduced exactly.

Defaults follow the submitted project report (Section 5.3): common cycle
C = 60 s, coordinated green G = 30 s, 5-second offset resolution, 400 m links,
40 km/h nominal speed, and a 20-vehicle platoon released at 1-second headways in
each direction.

Objective function: ``J = alpha * W + beta * S`` where ``W`` is total simulated
waiting time (seconds) and ``S`` the number of stops. Default weights are
``alpha = 1.0`` and ``beta = 2.0``: waiting time is the primary operational
metric (seconds), and one stop is weighted like two seconds of delay, since a
stop costs extra travel time, fuel and comfort even when the red wait itself is
short. Both weights are configurable for sensitivity analysis.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

DirectionMode = Literal["forward", "reverse", "both"]
DemandLevel = Literal["low", "medium", "high", "custom"]

DEMAND_PRESETS: dict[str, dict[str, float]] = {
    # vehicles_per_direction and headway define a released platoon of traffic.
    "low": {"vehicles_per_direction": 10, "headway_s": 3.0},
    "medium": {"vehicles_per_direction": 20, "headway_s": 1.0},
    "high": {"vehicles_per_direction": 50, "headway_s": 1.0},
}

__all__ = ["DEMAND_PRESETS", "ScenarioConfig", "offset_domain"]


@dataclass
class ScenarioConfig:
    """Full, validated specification of one coordination scenario.

    Attributes:
        n_intersections: Number of signalized intersections N (>= 2).
        cycle_length: Common cycle length C in seconds.
        green_duration: Coordinated green duration G in seconds (0 < G <= C).
        link_distance_m: Link length (metres) applied to every inter-intersection
            link. For unequal spacing use :attr:`link_distances_m`.
        link_distances_m: Optional explicit per-link distances; overrides
            ``link_distance_m`` when provided (length must be N - 1).
        speed_kmh: Nominal progression speed in km/h.
        demand_level: One of ``low``/``medium``/``high``/``custom``.
        vehicles_per_direction: Vehicles released in each enabled direction.
        headway_s: Departure headway inside a platoon (seconds).
        departure_pattern: ``"platoon"`` or ``"uniform"`` release pattern.
        direction_mode: Which directions to simulate: ``both``, ``forward`` or
            ``reverse``.
        departure_start_s: Time at which the platoon/release starts (seconds).
        jitter_s: Maximum +/- uniform arrival jitter in seconds (0 disables; a
            seeded RNG makes it reproducible).
        seed: Random seed used for departure jitter (stored for reproducibility).
        offset_resolution_s: Discretization step of the offset domain (must
            divide the cycle length exactly; first offset O_1 = 0 is fixed).
        objective_weight_wait: ``alpha`` in J = alpha*W + beta*S (>= 0).
        objective_weight_stop: ``beta`` in J = alpha*W + beta*S (>= 0).
        progression_tolerance_s: Optional hard progression constraint: for every
            adjacent pair (i, i+1) the circular distance between the achieved
            offset difference (O_{i+1} - O_i) mod C and the nominal travel time
            tau_i (mod C) must not exceed ``progression_tolerance_s``. ``None``
            disables the constraint; values in (0, C/2] are accepted. A value of
            C/2 is always satisfiable and therefore prunes nothing.

    """

    n_intersections: int = 5
    cycle_length: float = 60.0
    green_duration: float = 30.0
    link_distance_m: float = 400.0
    link_distances_m: tuple[float, ...] | None = None
    speed_kmh: float = 40.0

    demand_level: DemandLevel = "medium"
    vehicles_per_direction: int = 20
    headway_s: float = 1.0
    departure_pattern: Literal["platoon", "uniform"] = "platoon"
    direction_mode: DirectionMode = "both"
    departure_start_s: float = 0.0
    jitter_s: float = 0.0
    seed: int = 42

    offset_resolution_s: float = 5.0

    objective_weight_wait: float = 1.0
    objective_weight_stop: float = 2.0

    progression_tolerance_s: float | None = None

    def __post_init__(self) -> None:
        errors: list[str] = [
            self._check("n_intersections", self.n_intersections, lambda v: 2 <= v <= 20),
            self._check("cycle_length", self.cycle_length, lambda v: 0 < v <= 3600),
            self._check(
                "green_duration",
                self.green_duration,
                lambda v: 0 < v <= self.cycle_length,
            ),
            self._check("link_distance_m", self.link_distance_m, lambda v: 0 < v <= 10_000),
            self._check("speed_kmh", self.speed_kmh, lambda v: 0 < v <= 200),
        ]
        if self.link_distances_m is not None:
            errors.append(
                self._check(
                    "link_distances_m",
                    len(self.link_distances_m),
                    lambda v: v == self.n_intersections - 1,
                )
            )
            for k, d in enumerate(self.link_distances_m):
                errors.append(self._check(f"link_distances_m[{k}]", d, lambda x: 0 < x <= 10_000))
        errors.append(
            self._check(
                "vehicles_per_direction",
                self.vehicles_per_direction,
                lambda v: 1 <= v <= 500,
            )
        )
        errors.append(self._check("headway_s", self.headway_s, lambda v: 0 < v <= 60))
        if self.departure_pattern not in ("platoon", "uniform"):
            errors.append(
                self._check("departure_pattern", self.departure_pattern, lambda v: False)
            )
        if self.direction_mode not in ("forward", "reverse", "both"):
            errors.append(self._check("direction_mode", self.direction_mode, lambda v: False))
        errors.append(self._check("departure_start_s", self.departure_start_s, lambda v: v >= 0))
        errors.append(self._check("jitter_s", self.jitter_s, lambda v: 0 <= v <= 30))
        errors.append(
            self._check("offset_resolution_s", self.offset_resolution_s, lambda v: 0 < v)
        )
        errors.append(
            self._check(
                "objective_weight_wait", self.objective_weight_wait, lambda v: v >= 0
            )
        )
        errors.append(
            self._check("objective_weight_stop", self.objective_weight_stop, lambda v: v >= 0)
        )
        if self.progression_tolerance_s is not None:
            errors.append(
                self._check(
                    "progression_tolerance_s",
                    self.progression_tolerance_s,
                    lambda v: 0 < v <= self.cycle_length / 2,
                )
            )

        # The offset domain must divide the cycle exactly so that the domain is
        # a complete, non-overlapping grid over [0, C).
        if self.cycle_length > 0:
            steps = self.cycle_length / self.offset_resolution_s
            if abs(steps - round(steps)) > 1e-9:
                raise ValueError(
                    "offset_resolution_s must divide cycle_length exactly "
                    f"(C={self.cycle_length}, resolution={self.offset_resolution_s})"
                )

        if any(e is not None for e in errors):
            raise ValueError(
                "Invalid scenario configuration: " + "; ".join(e for e in errors if e is not None)
            )

        # demand_level is a label describing the configuration; named presets
        # ('low'/'medium'/'high') are expanded by the UI and benchmark runner,
        # which write explicit vehicles_per_direction/headway_s values. Anything
        # else is recorded as 'custom' so saved metadata stays truthful.
        if self.demand_level not in DEMAND_PRESETS:
            self.demand_level = "custom"

    @staticmethod
    def _check(name: str, value: Any, predicate: Any) -> str | None:
        """Return an error message when ``predicate(value)`` is False."""
        try:
            ok = predicate(value)
        except Exception:  # noqa: BLE001 - predicate issues count as invalid
            ok = False
        if ok:
            return None
        return f"{name}={value!r}"

    # -- derived properties ---------------------------------------------------

    @property
    def n_steps(self) -> int:
        """Number of discrete offsets available per intersection (C / resolution)."""
        return int(round(self.cycle_length / self.offset_resolution_s))

    @property
    def offsets_per_intersection(self) -> int:
        """Same as :attr:`n_steps`; the CSP domain size D."""
        return self.n_steps

    @property
    def effective_link_distances_m(self) -> tuple[float, ...]:
        """Per-link distances: explicit values when given, else the uniform value."""
        if self.link_distances_m is not None:
            return tuple(self.link_distances_m)
        return tuple(self.link_distance_m for _ in range(self.n_intersections - 1))

    @property
    def search_space_size(self) -> int:
        """Raw number of offset combinations with O_1 fixed: D^(N-1).

        This is the size of the state space before constraint propagation,
        backtracking, or branch-and-bound pruning.
        """
        return self.offsets_per_intersection ** (self.n_intersections - 1)

    @property
    def directions(self) -> tuple[str, ...]:
        """Directions that will be simulated, as configured by ``direction_mode``."""
        if self.direction_mode == "both":
            return ("forward", "reverse")
        return (self.direction_mode,)

    def offset_grid(self) -> tuple[float, ...]:
        """Return the legal offset domain D = {0, r, 2r, ..., C - r}.

        The resolution ``r`` is ``offset_resolution_s``; the grid always
        includes 0 and excludes the cycle length itself.
        """
        return tuple(i * self.offset_resolution_s for i in range(self.n_steps))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable replica of the configuration."""
        data = asdict(self)
        if self.link_distances_m is not None:
            data["link_distances_m"] = list(self.link_distances_m)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScenarioConfig:
        """Rebuild a configuration from :meth:`to_dict` output (validating it)."""
        visible = {f for f in cls.__dataclass_fields__ if f in data}
        kwargs = {k: data[k] for k in visible}
        if isinstance(kwargs.get("link_distances_m"), list):
            kwargs["link_distances_m"] = tuple(kwargs["link_distances_m"])
        return cls(**kwargs)


def offset_domain(config: ScenarioConfig) -> tuple[float, ...]:
    """Return the legal offset domain for every intersection in ``config``."""
    return config.offset_grid()
