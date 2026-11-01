import base64
import re

import pytest

from traffic_coordination import ui_theme as ui
from traffic_coordination.dashboard import common
from traffic_coordination.signal_timing import is_green

GO_DELAY = re.compile(r"animation:go [0-9.]+s steps\(1, end\) (-?[0-9.]+)s")


def _delays(svg: str) -> list[float]:
    return [float(d) for d in GO_DELAY.findall(svg)]


def test_signal_row_lamps_are_in_phase_with_the_signal_model():
    offsets = (0.0, 40.0, 10.0, 40.0, 15.0)
    cycle, green = 60.0, 30.0
    delays = _delays(ui.signal_row_svg(offsets, cycle, green))
    assert len(delays) == len(offsets)
    for offset, delay in zip(offsets, delays, strict=True):
        for t in (0.0, 7.0, 29.0, 31.0, 44.0, 59.0, 83.0):
            # animation progress (0..1) at real time t, with time scaled by TIME_SCALE
            progress = ((t / ui.TIME_SCALE - delay) / (cycle / ui.TIME_SCALE)) % 1.0
            lamp_green = progress < green / cycle
            assert lamp_green == is_green(t, offset, cycle, green), (offset, t)


def test_signal_row_embeds_the_svg_as_an_image():
    html = ui.signal_row((0.0, 35.0), 60.0, 30.0)
    src = re.search(r'src="data:image/svg\+xml;base64,([^"]+)"', html)
    assert src is not None
    assert base64.b64decode(src.group(1)).decode("utf-8").startswith("<svg")
    assert "<svg" not in html  # inline SVG would be stripped by st.html's sanitizer
    assert "Light 2" in html and "+35 s" in html


def test_builders_escape_untrusted_text():
    html = (
        ui.plan_table(["<b>x</b>"], [["a & b"]])
        + ui.section("<script>")
        + ui.terms([("<i>t</i>", "1 < 2", "trusted <b>ok</b>")])
    )
    assert "<b>x</b>" not in html and "&lt;b&gt;" in html
    assert "a &amp; b" in html and "<script>" not in html
    assert "1 &lt; 2" in html and "trusted <b>ok</b>" in html


def test_strategy_cards_outline_lowest_score_and_scale_bars():
    cards = [
        ui.StrategyCard("uncoordinated", "None", "d", "Fixed rule", "neutral", 86.5, 4.0, 3780),
        ui.StrategyCard("csp", "Optimized search", "d", "Best possible", "ok", 13.5, 0.97, 618),
    ]
    html = ui.strategy_cards(cards)
    assert html.count('class="ui-card best"') == 1
    assert "width:100.00%" in html
    assert f"width:{618 / 3780 * 100:.2f}%" in html
    assert ui.strategy_cards([]) == ""


def test_stat_grid_shows_baseline_and_change():
    html = ui.stat_grid([ui.Stat("Waiting per car", "13.5", "s", "86.5 s", "-84%")])
    assert "was 86.5 s" in html and "-84%" in html


def test_default_road_maps_to_the_report_scenario():
    config = common.road_to_config(common.ROAD_DEFAULTS)
    assert config.n_intersections == 5
    assert config.vehicles_per_direction == 20 and config.headway_s == 1.0
    assert config.direction_mode == "both" and config.departure_pattern == "platoon"
    assert config.progression_tolerance_s == 10.0
    assert config.objective_weight_wait == 1.0 and config.objective_weight_stop == 2.0


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        ({"green_s": 90}, "cannot be longer"),
        ({"cycle_s": 65, "step_s": 2}, "divide the cycle"),
        ({"cycle_s": 30, "green_s": 20, "tolerance_s": 0}, None),
    ],
)
def test_road_problem_explains_invalid_roads(change, fragment):
    road = {**common.ROAD_DEFAULTS, **change}
    problem = common.road_problem(road)
    if fragment is None:
        assert problem is None
    else:
        assert problem is not None and fragment in problem


def test_tolerance_off_disables_the_constraint():
    config = common.road_to_config({**common.ROAD_DEFAULTS, "tolerance_s": 0})
    assert config.progression_tolerance_s is None
