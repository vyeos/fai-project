"""Page 1: describe a road and get the best timing plan for its lights."""

from __future__ import annotations

from typing import Any

import streamlit as st

from traffic_coordination import ui_theme as ui
from traffic_coordination.metrics import STATUS_NO_SOLUTION
from traffic_coordination.scenario_generator import build_corridor
from traffic_coordination.ui_state import RunBundle
from traffic_coordination.visualization import (
    COLOR_FORWARD,
    COLOR_GREEN,
    COLOR_RED,
    COLOR_REVERSE,
)
from traffic_coordination.visualization.time_space import time_space_figure

from . import common

TOLERANCE_LABELS = {5: "±5 s", 10: "±10 s", 15: "±15 s", 0: "Off"}


def road_form(road: dict[str, Any]) -> dict[str, Any] | None:
    """Draw the input form; return the new road description when submitted."""
    with st.form("road_form"):
        lights = st.slider("Number of traffic lights", 2, 8, road["lights"])
        distance = st.slider(
            "Distance between lights", 100, 1000, road["distance_m"], 50, format="%d m"
        )
        speed = st.slider("Speed limit", 20, 80, road["speed_kmh"], 5, format="%d km/h")
        traffic = st.radio(
            "Traffic",
            list(common.TRAFFIC),
            index=list(common.TRAFFIC).index(road["traffic"]),
            horizontal=True,
            help="Light: 10 cars each way, 3 s apart. Moderate: 20 cars each way, "
            "1 s apart. Heavy: 50 cars each way, 1 s apart.",
        )
        directions = st.radio(
            "Cars drive",
            list(common.DIRECTIONS),
            index=list(common.DIRECTIONS).index(road["directions"]),
            horizontal=True,
            help="One way is easy to coordinate. Both ways forces a compromise, because "
            "a perfect wave in one direction is usually a bad one in the other.",
        )
        arrivals = st.radio(
            "Cars arrive",
            list(common.ARRIVALS),
            index=list(common.ARRIVALS).index(road["arrivals"]),
            horizontal=True,
            help="In a bunch: a queue of cars arriving together, like after a red light "
            "upstream. Spread out: a steady trickle across a whole cycle.",
        )
        with st.expander("Light timing and optimizer settings"):
            cycle_col, green_col = st.columns(2)
            with cycle_col:
                cycle = st.number_input(
                    "Cycle length (s)",
                    30,
                    180,
                    road["cycle_s"],
                    5,
                    help="Seconds before a light repeats its green-then-red pattern. "
                    "Every light uses the same cycle.",
                )
            with green_col:
                green = st.number_input(
                    "Green time (s)",
                    5,
                    180,
                    road["green_s"],
                    5,
                    help="How long each light stays green for this road in every cycle.",
                )
            step = st.select_slider(
                "Timing step",
                [1, 2, 5, 10],
                road["step_s"],
                format_func=lambda v: f"{v} s",
                help="Start times are chosen in steps of this size. Smaller steps mean "
                "finer plans and many more plans to search.",
            )
            tolerance = st.select_slider(
                "Green-wave rule",
                list(TOLERANCE_LABELS),
                road["tolerance_s"],
                format_func=TOLERANCE_LABELS.get,
                help="Each light must start within this many seconds of the driving time "
                "from the previous light. It shrinks the search a lot. Off searches "
                "every combination.",
            )
            stop_cost = st.slider(
                "Cost of one stop",
                0.0,
                10.0,
                float(road["stop_cost"]),
                0.5,
                format="%.1f s",
                help="The score is total waiting seconds plus this many seconds for "
                "every stop. Raise it to favour fewer stops over shorter waits.",
            )
        submitted = st.form_submit_button("Find the best timings", type="primary", width="stretch")
    if not submitted:
        return None
    return {
        "lights": lights,
        "distance_m": distance,
        "speed_kmh": speed,
        "traffic": traffic,
        "directions": directions,
        "arrivals": arrivals,
        "cycle_s": int(cycle),
        "green_s": int(green),
        "step_s": step,
        "tolerance_s": tolerance,
        "stop_cost": stop_cost,
    }


def headline(bundle: RunBundle) -> None:
    """Show the one-sentence answer and its three supporting numbers."""
    config = bundle.config
    wait0, stops0 = common.per_car(bundle.uncoordinated)
    wait1, stops1 = common.per_car(bundle.csp)
    score0 = bundle.uncoordinated.simulation.objective
    score1 = bundle.csp.simulation.objective
    label, tone = common.status_label(bundle.csp)

    if wait0 <= 0 and stops0 <= 0:
        sentence = "On this road no car ever waits, even with no coordination at all."
    else:
        sentence = (
            f"With optimized timings an average car waits <b>{wait1:.0f} s</b> instead of "
            f"{wait0:.0f} s, and stops <b>{stops1:.1f}</b> times instead of {stops0:.1f}."
        )
    note = (
        f"{common.road_sentence(config)} Driving from one light to the next takes about "
        f"{common.link_seconds(config):.0f} s."
    )
    status = {
        "Best possible": "Proven best plan for this road",
        "Best found in time": "Best plan found before the time limit (not proven best)",
    }.get(label, label)
    st.html(ui.summary(sentence, note, ui.badge(status, tone)))
    st.html(
        ui.stat_grid(
            [
                ui.Stat("Waiting per car", f"{wait1:.1f}", "s", f"{wait0:.1f} s", common.drop(wait0, wait1)),
                ui.Stat("Stops per car", f"{stops1:.2f}", "", f"{stops0:.2f}", common.drop(stops0, stops1)),
                ui.Stat("Score (lower is better)", f"{score1:,.0f}", "", f"{score0:,.0f}", common.drop(score0, score1)),
            ]
        )
    )


def plan_section(bundle: RunBundle) -> None:
    """When each light turns green, as moving lights and as a table."""
    config = bundle.config
    offsets = bundle.csp.plan.offsets
    tau = common.link_seconds(config)
    st.html(
        ui.section(
            "When each light turns green",
            f"Every light repeats the same {config.cycle_length:g}-second cycle: "
            f"{config.green_duration:g} s green, then red. The plan only decides <b>when</b> "
            "each light starts its green, measured from Light 1.",
        )
    )
    st.html(ui.signal_row(offsets, config.cycle_length, config.green_duration))
    rows = [["Light 1", "0 s", "Reference point", "—"]]
    for i in range(1, len(offsets)):
        gap = (offsets[i] - offsets[i - 1]) % config.cycle_length
        rows.append([f"Light {i + 1}", f"+{offsets[i]:g} s", f"{gap:g} s", f"{tau:.0f} s"])
    st.html(
        ui.plan_table(
            ["Light", "Green starts at", "Later than the light before", "Driving time from it"],
            rows,
        )
    )


def difference_section(bundle: RunBundle) -> None:
    """Side-by-side time-space diagrams: no coordination vs optimized."""
    st.html(
        ui.section(
            "See the difference",
            "Each line is one car. Time runs left to right and the road runs from Light 1 "
            "at the bottom to the last light at the top. A car moving freely draws a "
            "straight slope. A car stopped at a red light runs <b>flat along the red bar</b> "
            "until the light turns green, and the bunch of cars squeezes together.",
        )
    )
    st.html(
        ui.legend(
            [
                (COLOR_GREEN, "Light is green", True),
                (COLOR_RED, "Light is red", True),
                (COLOR_FORWARD, "Car heading up the road", False),
                (COLOR_REVERSE, "Car heading down the road", False),
            ]
        )
    )
    corridor = build_corridor(bundle.config)
    sims = {alg: common.traced(bundle, alg) for alg in ("uncoordinated", "csp")}
    horizon = max(
        max(t.departure_from_intersection.values())
        for sim in sims.values()
        for t in sim.vehicle_traces
        if t.departure_from_intersection
    ) + 16
    left, right = st.columns(2, gap="medium")
    for column, alg, title in (
        (left, "uncoordinated", "No coordination"),
        (right, "csp", "Optimized search"),
    ):
        with column:
            fig = time_space_figure(
                corridor,
                bundle.config,
                tuple(sims[alg].plan.offsets),
                sims[alg],
                horizon_s=horizon,
                title=title,
                height=400,
                show_legend=False,
            )
            common.chart(fig, key=f"ts_{alg}")


def render() -> None:
    """Draw the page."""
    road = common.get_road()
    st.html(
        ui.page_header(
            "Time the traffic lights on a road",
            "Describe a straight road with a few traffic lights. The model works out "
            "<b>when each light should turn green</b> so cars hit as few red lights as "
            "possible, and shows how much waiting that saves compared with lights that "
            "are not coordinated.",
        )
    )
    form_col, result_col = st.columns([0.36, 0.64], gap="large")
    with form_col:
        new_road = road_form(road)
    problem = common.road_problem(new_road) if new_road is not None else None
    if new_road is not None and problem is None:
        road.update(new_road)
        with result_col, st.spinner("Searching for the best timings..."):
            common.run_road(road)

    with result_col:
        if problem:
            st.html(
                ui.callout(
                    f"<b>That road can't be simulated.</b> {problem} The results below are "
                    "still for your last valid road.",
                    "bad",
                )
            )
        bundle = common.current_bundle()
        if bundle.csp.status == STATUS_NO_SOLUTION:
            st.html(
                ui.callout(
                    "<b>No plan satisfies the green-wave rule.</b> Widen the rule or turn "
                    "it off in the optimizer settings.",
                    "bad",
                )
            )
            return
        headline(bundle)
        plan_section(bundle)

    difference_section(bundle)
    st.html(
        ui.section(
            "Three ways to time the lights",
            "The same cars were simulated under three plans. The score adds up every "
            f"second spent waiting plus {bundle.config.objective_weight_stop:g} s for each "
            "stop, so lower is better.",
        )
    )
    st.html(common.strategy_cards(bundle))
    st.write("")
    common.link_to("how", "How does the optimizer find its plan?")
