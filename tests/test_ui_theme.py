import base64
import re

from traffic_coordination import ui_theme as ui
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


def test_masthead_embeds_the_signal_row_as_an_image():
    html = ui.masthead((0.0, 35.0), 60.0, 30.0, "CSP plan", "Eyebrow")
    src = re.search(r'src="data:image/svg\+xml;base64,([^"]+)"', html)
    assert src is not None
    assert base64.b64decode(src.group(1)).decode("utf-8").startswith("<svg")
    assert "<svg" not in html  # inline SVG would be stripped by st.html's sanitizer


def test_masthead_without_offsets_renders_title_only():
    html = ui.masthead(None, 0.0, 0.0, "", "Eyebrow")
    assert "tc-wave" not in html and "<h1>" in html


def test_builders_escape_untrusted_text():
    html = ui.spec_sheet([("<b>x</b>", "a & b")]) + ui.section_title("<script>", "01")
    assert "<b>x</b>" not in html and "&lt;b&gt;" in html
    assert "a &amp; b" in html and "<script>" not in html


def test_ledger_marks_lowest_objective_and_scales_bars():
    rows = [
        ui.LedgerRow("uncoordinated", "fixed plan", "neutral", 3460, 160, 3780),
        ui.LedgerRow("csp", "proven optimal", "ok", 540, 39, 618),
    ]
    html = ui.ledger(rows)
    assert html.count('class="row best"') == 1
    assert "width:100.00%" in html
    assert f"width:{618 / 3780 * 100:.2f}%" in html
    assert ui.ledger([]) == ""
