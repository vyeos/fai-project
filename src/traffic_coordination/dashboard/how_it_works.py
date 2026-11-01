"""Page 2: the problem, the vocabulary, the simulator and the search, in plain words."""

from __future__ import annotations

import streamlit as st

from traffic_coordination import ui_theme as ui
from traffic_coordination.metrics import FEASIBLE_OPTIMAL
from traffic_coordination.scenario_generator import build_corridor
from traffic_coordination.ui_state import RunBundle
from traffic_coordination.visualization.corridor import corridor_figure
from traffic_coordination.visualization.timeline import signal_timeline_figure

from . import common


def problem_section(bundle: RunBundle) -> None:
    """Why uncoordinated lights make cars stop, and what a green wave is."""
    config = bundle.config
    tau = common.link_seconds(config)
    arrives = tau % config.cycle_length
    if arrives >= config.green_duration:
        outcome = "by then Light 2 has already turned red, so the car stops and waits"
    else:
        outcome = (
            "Light 2 is still green for that car, but the cars behind it arrive later "
            "and some of them meet red"
        )
    st.html(
        ui.section(
            "The problem",
            f"Picture {config.n_intersections} traffic lights along one straight road, "
            f"{config.link_distance_m:g} m apart. At {config.speed_kmh:g} km/h a car needs "
            f"about <b>{tau:.0f} s</b> to get from one light to the next.",
            f"If every light turns green at the same moment, a car that leaves Light 1 as "
            f"it turns green reaches Light 2 after {tau:.0f} s, and {outcome}. The same "
            "thing repeats further down the road.",
            "The fix is to <b>delay</b> each light's green so it lines up with the cars "
            "coming from the light before. Drivers call this a <b>green wave</b>. Choosing "
            "the best delays is the whole job of the model.",
            first=True,
        )
    )
    offsets = tuple(bundle.csp.plan.offsets)
    common.chart(
        signal_timeline_figure(offsets, config, 4 * config.cycle_length), key="how_timeline"
    )
    st.caption(
        "Green bars: when each light is green in the optimized plan for your road. "
        "Each row is shifted to the right of the one before it. That shift is the delay."
    )


def terms_section(bundle: RunBundle) -> None:
    """Glossary with the reader's own values."""
    config = bundle.config
    offsets = bundle.csp.plan.offsets
    example = f"+{offsets[1]:g} s" if len(offsets) > 1 else ""
    st.html(
        ui.section(
            "Words used on this site",
            "Seven terms are enough to follow every page. The values are from your road.",
        )
    )
    st.html(
        ui.terms(
            [
                (
                    "Cycle",
                    f"{config.cycle_length:g} s",
                    "How long a light takes to go through green and red once. All lights "
                    "share it, so the whole pattern repeats every cycle.",
                ),
                (
                    "Green time",
                    f"{config.green_duration:g} s",
                    "The part of each cycle that a light is green for cars on this road.",
                ),
                (
                    "Offset (delay)",
                    example,
                    "How many seconds after Light 1 a light starts its green. A "
                    "<b>timing plan</b> is just one offset per light; Light 1 is always 0.",
                ),
                (
                    "Driving time",
                    f"{common.link_seconds(config):.0f} s",
                    "Distance between two lights divided by the speed limit.",
                ),
                (
                    "Stop",
                    "",
                    "One car arriving at one red light. A car that meets three reds has "
                    "made three stops.",
                ),
                (
                    "Waiting time",
                    "",
                    "Seconds a car spends standing at red lights, added up over the trip.",
                ),
                (
                    "Score",
                    f"wait + {config.objective_weight_stop:g} × stops",
                    "One number to compare plans: all waiting seconds plus "
                    f"{config.objective_weight_stop:g} s per stop. Lower is better. A stop "
                    "is charged extra because braking and pulling away cost time and fuel "
                    "even when the wait is short.",
                ),
            ]
        )
    )


def simulator_section(bundle: RunBundle) -> None:
    """List the five rules the simulator follows to score a plan."""
    config = bundle.config
    cars = len(config.directions) * config.vehicles_per_direction
    if config.departure_pattern == "platoon":
        release = f"in a bunch, {config.headway_s:g} s apart"
    else:
        release = "spread evenly over at least one cycle"
    st.html(
        ui.section(
            "How a plan is scored",
            "A small simulator drives every car down the road under a given plan. It is "
            "deterministic: the same plan and the same cars always give the same score, so "
            "the strategies are compared fairly.",
        )
    )
    st.html(
        ui.steps(
            [
                (
                    "Create the traffic",
                    f"{cars} cars enter the road {release}. Every strategy is scored on "
                    "exactly these cars.",
                ),
                (
                    "Arrive at a light",
                    "If the light is green when the car arrives, it drives straight through.",
                ),
                (
                    "Wait at red",
                    "If it is red, the car waits until it turns green again. That wait is "
                    "added to the car's waiting time and counts as one stop.",
                ),
                (
                    "Drive to the next light",
                    f"The car then needs {common.link_seconds(config):.0f} s to reach the "
                    "next light, always at the speed limit.",
                ),
                (
                    "Add it up",
                    "Waiting time and stops are summed over every car and every light to "
                    "give the plan's score.",
                ),
            ]
        )
    )


def strategies_section(bundle: RunBundle) -> None:
    """Describe the baselines, working the greedy rule through."""
    config = bundle.config
    tau = common.link_seconds(config)
    greedy = bundle.greedy.plan.offsets
    worked = ""
    if len(greedy) > 2:
        raw = greedy[1] + tau
        worked = (
            f" On your road: Light 2 gets {tau:.0f} s rounded to the {config.offset_resolution_s:g} s "
            f"step, so +{greedy[1]:g} s. Light 3 gets {greedy[1]:g} + {tau:.0f} = {raw:.0f} s, "
            f"which wraps around the {config.cycle_length:g} s cycle and rounds to "
            f"+{greedy[2]:g} s."
        )
    st.html(
        ui.section(
            "Three strategies",
            "Every strategy produces a timing plan. Only the third one searches.",
        )
    )
    st.html(
        ui.steps(
            [
                (
                    "No coordination",
                    "All offsets are 0, so every light turns green together. It is the "
                    "baseline that shows what coordination is worth.",
                ),
                (
                    "Simple green wave",
                    "Start Light 1 at 0, then give each light the previous light's offset "
                    "plus the driving time between them." + worked + " This is perfect "
                    "for cars driving up the road and usually poor for cars driving down it.",
                ),
                (
                    "Optimized search",
                    "Treats the offsets as a puzzle with rules and searches for the plan "
                    "with the lowest score, explained next.",
                ),
            ]
        )
    )


def search_section(bundle: RunBundle) -> None:
    """Explain the CSP formulation and search, with this run's numbers."""
    config = bundle.config
    csp = bundle.csp
    stats = csp.metadata.get("search_stats", {})
    space = config.search_space_size
    choices = config.offsets_per_intersection
    grid = ", ".join(f"{v:g}" for v in config.offset_grid()[:3])
    tol = config.progression_tolerance_s
    rule = (
        f"Each light's offset must be within ±{tol:g} s of the previous light's offset "
        "plus the driving time. Plans that break it are never scored. It keeps the search "
        "small and the plans sensible."
        if tol is not None
        else "Your run has this rule switched off, so every plan is allowed and the search "
        "has to consider all of them."
    )
    if csp.status == FEASIBLE_OPTIMAL:
        answer = (
            f"Every allowed plan was either scored or safely ruled out, so the best plan "
            f"found is <b>the best possible</b> under the rules. On your road the search "
            f"scored {csp.complete_assignments_evaluated:,} of the {space:,} plans."
        )
    else:
        answer = (
            "The search hit its time or size limit before finishing, so the plan shown is "
            "the best it found, and it says so instead of claiming it is the best possible. "
            f"It scored {csp.complete_assignments_evaluated:,} of the {space:,} plans."
        )
    st.html(
        ui.section(
            "How the optimized search works",
            "This is the AI part of the project. Choosing offsets is set up as a "
            "<b>constraint satisfaction problem</b> (CSP): a set of unknowns, the values "
            "each may take, and rules they must obey. A classic search then finds the "
            "best combination.",
        )
    )
    st.html(
        ui.steps(
            [
                (
                    "Unknowns and their choices",
                    f"The unknowns are the offsets of Lights 2 to {config.n_intersections} "
                    f"(Light 1 stays at 0). Each can be one of {choices} values ({grid}, … "
                    f"s), which makes {choices}<sup>{config.n_intersections - 1}</sup> = "
                    f"<b>{space:,}</b> possible plans.",
                ),
                ("The green-wave rule", rule),
                (
                    "Backtracking",
                    "The search fixes Light 2, then Light 3, and so on, like walking down a "
                    "tree of choices. At the end of a branch it scores the full plan, then "
                    "steps back and tries the next value.",
                ),
                (
                    "Forward checking",
                    "As soon as a light gets a value, values for the next light that would "
                    "break the rule are crossed out, so they are never tried. On your road "
                    f"that crossed out <b>{stats.get('forward_check_removals', 0):,}</b> "
                    "values.",
                ),
                (
                    "Branch and bound",
                    "The search remembers the best plan so far and may skip any branch that "
                    "cannot beat it. The estimate used here is very cautious (it assumes the "
                    "rest of the road adds no cost), so it is always safe but rarely skips "
                    f"anything: <b>{stats.get('branch_bound_prunes', 0):,}</b> skips on your "
                    "road.",
                ),
                ("The answer", answer),
            ]
        )
    )
    common.link_to("hood", "See the search step by step")


def corridor_section(bundle: RunBundle) -> None:
    """Corridor snapshot with a time slider for the optimized plan."""
    config = bundle.config
    sim = common.traced(bundle, "csp")
    st.html(
        ui.section(
            "Watch the road at any moment",
            "Drag the slider to move through time under the optimized plan. Each light "
            "shows its colour at that moment, and each triangle is a car pointing the way "
            "it drives.",
        )
    )
    end = max(
        (max(t.departure_from_intersection.values()) for t in sim.vehicle_traces),
        default=3 * config.cycle_length,
    )
    time_s = st.slider("Time (seconds)", 0, int(end) + 10, 0, 1, key="how_time")
    corridor = build_corridor(config)
    common.chart(
        corridor_figure(corridor, config, tuple(sim.plan.offsets), sim, float(time_s)),
        key="how_corridor",
    )


def limits_section() -> None:
    """List what the simplified model does not capture."""
    st.html(
        ui.section(
            "What the model leaves out",
            "To keep the search problem clear, the simulator simplifies real traffic. Every "
            "number on this site is simulated, not measured on a street.",
        )
    )
    st.html(
        ui.terms(
            [
                ("Constant speed", "", "Cars never speed up, slow down or overtake."),
                ("No queues", "", "Cars never block each other; a red light holds each car on its own."),
                ("One road only", "", "No turning traffic, side streets or pedestrian crossings."),
                ("Shared cycle", "", "Every light uses the same cycle and the same green time."),
            ]
        )
    )
    st.html(
        ui.section(
            "About this project",
            "Built for the Foundation of AI course (ECSCT24301) at Adani University to show "
            "how a classic AI technique, constraint satisfaction search, solves a "
            "planning problem, and to compare it honestly with simpler methods. It is a "
            "teaching model, not a tool for timing real traffic lights.",
        )
    )


def render() -> None:
    """Draw the page."""
    bundle = common.current_bundle()
    st.html(
        ui.page_header(
            "How it works",
            "Everything behind the result on the first page, in plain words. The numbers "
            f"come from the road you last ran: {common.road_sentence(bundle.config)}",
        )
    )
    problem_section(bundle)
    terms_section(bundle)
    simulator_section(bundle)
    strategies_section(bundle)
    search_section(bundle)
    corridor_section(bundle)
    limits_section()
