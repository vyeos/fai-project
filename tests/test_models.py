"""Tests for the domain models (corridor, timing plan, vehicles)."""

import pytest

from traffic_coordination.models import (
    Corridor,
    Intersection,
    TimingPlan,
    VehicleSpec,
    timing_plan,
)


class TestIntersection:
    def test_valid_intersection(self) -> None:
        it = Intersection(index=2, name="I3", position_m=800.0)
        assert it.index == 2
        assert it.position_m == 800.0

    def test_negative_index_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            Intersection(index=-1, name="I0", position_m=0.0)

    def test_nonfinite_position_rejected(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            Intersection(index=0, name="I1", position_m=float("nan"))


class TestCorridor:
    def make(self, distances=(400.0, 600.0, 250.0)):
        positions = [0.0]
        for d in distances:
            positions.append(positions[-1] + d)
        intersections = tuple(
            Intersection(index=i, name=f"I{i + 1}", position_m=p)
            for i, p in enumerate(positions)
        )
        return Corridor(intersections=intersections, link_distances_m=tuple(distances))

    def test_counts_and_length(self) -> None:
        corridor = self.make()
        assert corridor.n_intersections == 4
        assert corridor.total_length_m == 1250.0

    def test_direction_sequences(self) -> None:
        corridor = self.make()
        assert corridor.link_indices_for_direction("forward") == (0, 1, 2, 3)
        assert corridor.link_indices_for_direction("reverse") == (3, 2, 1, 0)

    def test_shared_link_travel_time(self) -> None:
        corridor = self.make()
        forward = corridor.travel_time_between(0, 1, 40.0)
        reverse = corridor.travel_time_between(1, 0, 40.0)
        assert forward == reverse == pytest.approx(400 / (40 / 3.6))

    def test_nonadjacent_rejected(self) -> None:
        corridor = self.make()
        with pytest.raises(ValueError, match="not adjacent"):
            corridor.travel_time_between(0, 2, 40.0)

    def test_wrong_link_count_rejected(self) -> None:
        with pytest.raises(ValueError, match="link distances"):
            Corridor(
                intersections=(
                    Intersection(0, "I1", 0.0),
                    Intersection(1, "I2", 400.0),
                ),
                link_distances_m=(400.0, 100.0),
            )

    def test_decreasing_positions_rejected(self) -> None:
        with pytest.raises(ValueError, match="strictly increase"):
            Corridor(
                intersections=(
                    Intersection(0, "I1", 500.0),
                    Intersection(1, "I2", 0.0),
                ),
                link_distances_m=(400.0,),
            )


class TestTimingPlan:
    def test_reference_must_be_zero(self) -> None:
        with pytest.raises(ValueError, match="reference"):
            TimingPlan((5.0, 10.0, 20.0))

    def test_too_short_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            TimingPlan((0.0,))

    def test_negative_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            TimingPlan((0.0, -5.0))

    def test_indexing_and_iteration(self) -> None:
        plan = timing_plan([0, 10, 20])
        assert len(plan) == 3
        assert list(plan) == [0.0, 10.0, 20.0]
        assert plan[2] == 20.0

    def test_nonfinite_rejected(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            TimingPlan((0.0, float("inf")))


class TestVehicleSpec:
    def test_valid(self) -> None:
        vehicle = VehicleSpec(vehicle_id=1, direction="forward", departure_time=3.5)
        assert vehicle.direction == "forward"

    def test_bad_direction(self) -> None:
        with pytest.raises(ValueError, match="direction"):
            VehicleSpec(vehicle_id=1, direction="sideways", departure_time=0.0)

    def test_negative_departure(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            VehicleSpec(vehicle_id=1, direction="forward", departure_time=-1.0)

    def test_negative_id(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            VehicleSpec(vehicle_id=-1, direction="forward", departure_time=0.0)
