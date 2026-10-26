"""Tests for signal-timing arithmetic and the deterministic simulator."""

import pytest

from traffic_coordination.config import ScenarioConfig
from traffic_coordination.models import timing_plan
from traffic_coordination.scenario_generator import build_corridor, generate_vehicles
from traffic_coordination.signal_timing import (
    is_green,
    next_green_start,
    signal_wait,
    travel_time_seconds,
)
from traffic_coordination.simulator import simulate_plan


class TestSignalTiming:
    C, G = 60.0, 30.0

    def test_inside_green_window(self) -> None:
        # offset 10 -> green [10, 40), [70, 100), ...
        assert is_green(15.0, 10.0, self.C, self.G)
        assert not is_green(45.0, 10.0, self.C, self.G)
        # offset 0 -> green [0, 30)
        assert is_green(15.0, 0.0, self.C, self.G)
        assert not is_green(35.0, 0.0, self.C, self.G)

    def test_exact_start_is_green(self) -> None:
        assert is_green(10.0, 10.0, self.C, self.G)

    def test_exact_end_is_red(self) -> None:
        # Boundary rule: green windows are half-open [start, start+G).
        assert not is_green(40.0, 10.0, self.C, self.G)

    def test_wait_to_next_window(self) -> None:
        # t=45, offset 10: next green starts at 70 -> wait 25 s.
        assert signal_wait(45.0, 10.0, self.C, self.G) == pytest.approx(25.0)

    def test_green_arrival_no_wait(self) -> None:
        assert signal_wait(12.0, 10.0, self.C, self.G) == 0.0

    def test_next_green_start_red_and_green(self) -> None:
        assert next_green_start(45.0, 10.0, self.C, self.G) == pytest.approx(70.0)
        assert next_green_start(12.0, 10.0, self.C, self.G) == pytest.approx(10.0)

    def test_validation(self) -> None:
        with pytest.raises(ValueError, match="0 <= O < C"):
            is_green(10.0, 60.0, self.C, self.G)
        with pytest.raises(ValueError, match="G <= C"):
            is_green(10.0, 0.0, self.C, self.C + 1.0)
        with pytest.raises(ValueError, match="non-negative"):
            is_green(-1.0, 0.0, self.C, self.G)


class TestTravelTime:
    def test_conversion_kmh_to_ms(self) -> None:
        # 400 m at 40 km/h (= 11.111 m/s) -> 36 s.
        assert travel_time_seconds(400.0, 40.0) == pytest.approx(36.0)

    def test_invalid_inputs(self) -> None:
        with pytest.raises(ValueError, match="distance"):
            travel_time_seconds(-1.0, 40.0)
        with pytest.raises(ValueError, match="Speed"):
            travel_time_seconds(400.0, 0.0)

    def test_zero_distance_is_zero_time(self) -> None:
        assert travel_time_seconds(0.0, 40.0) == 0.0


def build_setup(config: ScenarioConfig):
    return build_corridor(config), generate_vehicles(config)


class TestSimulation:
    def config(self, **overrides):
        return ScenarioConfig(n_intersections=3, **overrides)

    def test_uncoordinated_report_benchmark(self) -> None:
        """The all-zero plan reproduces the report's illustrative benchmark:
        5 intersections, medium demand -> 160 stops, 3,460 s waiting, 86.5 avg."""
        corridor, vehicles = build_setup(ScenarioConfig(n_intersections=5))
        result = simulate_plan(timing_plan([0.0] * 5), vehicles, ScenarioConfig(n_intersections=5))
        assert result.total_stops == 160
        assert result.total_waiting_time == pytest.approx(3460.0)
        assert result.average_waiting_time == pytest.approx(86.5)
        assert result.n_vehicles == 40

    def test_green_wave_forward_zero_stops_medium(self) -> None:
        """Offsets that align each link's travel time give forward zero stops.

        O_{i+1} = (O_i + 36) mod 60, i.e. grid values following the travel time.
        """
        config = self.config()
        corridor, vehicles = build_setup(config)
        # Perfectly-matched offsets need not be on the 5 s grid; use a fine grid.
        fine = ScenarioConfig(n_intersections=3, offset_resolution_s=1.0)
        _, fine_vehicles = build_setup(fine)
        plan = timing_plan([0.0, 36.0, 72.0 % 60.0])
        forward = [v for v in fine_vehicles if v.direction == "forward"]
        result = simulate_plan(plan, forward, fine)
        assert result.total_stops == 0
        assert result.total_waiting_time == pytest.approx(0.0)

    def test_stop_counts_per_red_arrival(self) -> None:
        """A vehicle stopped at two signals counts two stops."""
        config = self.config(direction_mode="forward", vehicles_per_direction=1, headway_s=5.0)
        _, vehicles = build_setup(config)
        plan = timing_plan([0.0, 0.0, 0.0])
        result = simulate_plan(plan, vehicles, config)
        # One vehicle departs at t=0, passes I1 green, arrives I2 at t=36 (red,
        # green [0,30)), waits 24, arrives I3 at t=96 -> r=36 -> red, waits 24.
        assert result.total_stops == 2
        assert result.total_waiting_time == pytest.approx(48.0)

    def test_plan_length_mismatch(self) -> None:
        config = self.config()
        _, vehicles = build_setup(config)
        with pytest.raises(ValueError, match="intersections"):
            simulate_plan(timing_plan([0.0, 0.0]), vehicles, config)

    def test_trace_collection(self) -> None:
        config = self.config()
        _, vehicles = build_setup(config)
        result = simulate_plan(timing_plan([0.0] * 3), vehicles, config, collect_traces=True)
        assert len(result.vehicle_traces) == len(vehicles)
        trace = result.vehicle_traces[0]
        assert set(trace.arrival_at_intersection) <= set(range(3))
        assert trace.total_wait == pytest.approx(sum(trace.wait_at_intersection.values()))

    def test_deterministic_no_randomness(self) -> None:
        config = self.config()
        _, vehicles = build_setup(config)
        plan = timing_plan([0.0, 5.0, 10.0])
        first = simulate_plan(plan, vehicles, config)
        second = simulate_plan(plan, vehicles, config)
        assert first.summary_dict() == second.summary_dict()


class TestScenarioGenerator:
    def test_platoon_pattern(self) -> None:
        config = ScenarioConfig(n_intersections=3, vehicles_per_direction=4, headway_s=2.0)
        vehicles = generate_vehicles(config)
        fwd = sorted(v.departure_time for v in vehicles if v.direction == "forward")
        assert fwd[0] == 0.0
        assert fwd == [0.0, 2.0, 4.0, 6.0]

    def test_uniform_pattern_spans_full_cycle(self) -> None:
        config = ScenarioConfig(
            n_intersections=3,
            vehicles_per_direction=4,
            headway_s=8.0,
            departure_pattern="uniform",
        )
        vehicles = generate_vehicles(config)
        fwd = sorted(v.departure_time for v in vehicles if v.direction == "forward")
        # horizon = max(C=60, 4*8=32) = 60 -> spacing 15 s.
        assert fwd == [0.0, 15.0, 30.0, 45.0]

    def test_uniform_horizon_never_below_platoon_span(self) -> None:
        config = ScenarioConfig(
            n_intersections=3,
            vehicles_per_direction=10,
            headway_s=10.0,
            departure_pattern="uniform",
        )
        fwd = sorted(
            v.departure_time
            for v in generate_vehicles(config)
            if v.direction == "forward"
        )
        # horizon = max(60, 100) = 100 -> spacing 10 s (density preserved)
        assert fwd == [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0]

    def test_seeded_jitter_is_reproducible(self) -> None:
        config = ScenarioConfig(n_intersections=3, vehicles_per_direction=5, jitter_s=0.5, seed=7)
        first = generate_vehicles(config)
        second = generate_vehicles(config)
        assert [(v.vehicle_id, v.departure_time) for v in first] == [
            (v.vehicle_id, v.departure_time) for v in second
        ]

    def test_reverse_direction_ids_unique(self) -> None:
        config = ScenarioConfig(n_intersections=3, vehicles_per_direction=4)
        vehicles = generate_vehicles(config)
        ids = [v.vehicle_id for v in vehicles]
        assert len(ids) == len(set(ids))

    def test_direction_mode_forward_only(self) -> None:
        config = ScenarioConfig(n_intersections=3, direction_mode="forward")
        vehicles = generate_vehicles(config)
        assert all(v.direction == "forward" for v in vehicles)
        assert len(vehicles) == 20


class TestConfigValidation:
    def test_green_must_not_exceed_cycle(self) -> None:
        with pytest.raises(ValueError, match="Invalid scenario configuration"):
            ScenarioConfig(green_duration=70.0)

    def test_resolution_must_divide_cycle(self) -> None:
        with pytest.raises(ValueError, match="divide cycle_length"):
            ScenarioConfig(offset_resolution_s=7.0)

    def test_negative_weights_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid scenario configuration"):
            ScenarioConfig(objective_weight_wait=-1.0)

    def test_search_space_size(self) -> None:
        config = ScenarioConfig(n_intersections=5)
        assert config.search_space_size == 12**4

    def test_offset_grid(self) -> None:
        assert ScenarioConfig().offset_grid() == (0.0, 5.0, 10.0, 15.0, 20.0, 25.0,
                                                  30.0, 35.0, 40.0, 45.0, 50.0, 55.0)

    def test_roundtrip_to_dict(self) -> None:
        config = ScenarioConfig(n_intersections=4, link_distances_m=(300.0, 500.0, 200.0))
        clone = ScenarioConfig.from_dict(config.to_dict())
        assert clone.to_dict() == config.to_dict()

    def test_progression_tolerance_bounds(self) -> None:
        with pytest.raises(ValueError, match="Invalid scenario configuration"):
            ScenarioConfig(progression_tolerance_s=40.0)  # > C/2
        config = ScenarioConfig(progression_tolerance_s=30.0)  # C/2 exactly is legal
        assert config.progression_tolerance_s == 30.0
