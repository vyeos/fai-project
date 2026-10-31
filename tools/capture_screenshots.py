"""Recapture the 15 dashboard screenshots in docs/screenshots/.

Start the dashboard first (``python -m streamlit run app.py --server.port 8599``),
then, from any environment with Playwright installed (``pip install playwright``;
it is not a project dependency):

    python tools/capture_screenshots.py docs/screenshots [http://localhost:8599]

It drives the locally installed Microsoft Edge headlessly at 1440x960, scale 1.5,
runs the default comparison and a demand sweep, and saves one PNG per view.
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1])
URL = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8599"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 960}, device_scale_factor=1.5)
        page.goto(URL)
        page.wait_for_selector(".tc-mast", timeout=60_000)
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(1500)

        def settle(ms: int = 1600) -> None:
            page.wait_for_timeout(ms)

        def tab(name: str) -> None:
            page.get_by_role("tab", name=name, exact=True).click()
            settle(900)

        def scroll_to(selector: str, block: str = "start") -> None:
            page.evaluate(
                "([s, b]) => { const els = [...document.querySelectorAll(s)]"
                ".filter(e => e.offsetParent); els[0].scrollIntoView({block: b}); }",
                [selector, block],
            )
            settle(700)

        def shot(name: str) -> None:
            page.screenshot(path=str(OUT / name))
            print("saved", name)

        # run the comparison from the Overview tab
        page.get_by_role("button", name="Run all algorithms").first.click()
        page.wait_for_selector(".tc-ledger .row.best", timeout=120_000)
        settle(2200)
        page.evaluate("document.querySelector('[data-testid=\"stMain\"]').scrollTo(0, 0)")
        settle()
        shot("01b_overview_top.png")
        scroll_to(".tc-overview", "start")
        shot("01_overview_last_run.png")

        tab("Corridor")
        scroll_to('[data-testid="stTabs"]')
        page.wait_for_selector('[data-testid="stTabPanel"] .js-plotly-plot', state="attached")
        settle()
        shot("02b_corridor_tab.png")
        page.evaluate(
            "[...document.querySelectorAll('.tc-section h3')]"
            ".find(h => h.innerText === 'Vehicle replay').scrollIntoView({block: 'start'})"
        )
        settle()
        shot("02_corridor_animation.png")

        # move the corridor time slider to t = 57 s
        scroll_to('[data-testid="stTabs"]')
        page.locator('input[type="range"][aria-label="View time t (s)"]').focus()
        for _ in range(57):
            page.keyboard.press("ArrowRight")
        # wait for the rerun to finish: the snapshot title reads the new time
        page.wait_for_function(
            "[...document.querySelectorAll('.gtitle')]"
            ".some(t => t.textContent.trim() === 't = 57 s')",
            timeout=60_000,
        )
        page.mouse.move(5, 5)
        settle(2500)
        shot("03_corridor_t57_vehicles.png")

        tab("Signals")
        scroll_to('[data-testid="stTabs"]')
        settle()
        shot("04_signals_timeline.png")

        tab("Algorithms")
        scroll_to('[data-testid="stTabs"]')
        shot("08_algorithms_tab.png")

        tab("Results")
        scroll_to('[data-testid="stTabs"]')
        settle(1800)
        shot("05_results_comparison.png")
        page.evaluate(
            "[...document.querySelectorAll('[data-testid=\"stPlotlyChart\"]')].filter(e=>e.offsetParent)[0]"
            ".scrollIntoView({block:'start'})"
        )
        settle()
        shot("05b_results_verification_plan.png")

        tab("Search inspector")
        scroll_to('[data-testid="stTabs"]')
        shot("06_search_inspector_stats.png")
        page.evaluate(
            "[...document.querySelectorAll('[data-testid=\"stPlotlyChart\"]')].filter(e=>e.offsetParent)[0]"
            ".scrollIntoView({block:'center'})"
        )
        settle()
        shot("06b_search_trace_charts.png")
        page.evaluate(
            "[...document.querySelectorAll('[data-testid=\"stDataFrame\"]')].filter(e=>e.offsetParent)[0]"
            ".scrollIntoView({block:'center'})"
        )
        settle()
        shot("06c_search_trace_events.png")

        tab("Sensitivity")
        page.get_by_role("button", name="Run sweep").click()
        page.wait_for_function(
            "[...document.querySelectorAll('[data-testid=\"stPlotlyChart\"]')].some(e=>e.offsetParent)",
            timeout=180_000,
        )
        settle(2500)
        scroll_to('[data-testid="stTabs"]')
        settle(1200)
        scroll_to('[data-testid="stTabs"]')
        shot("07_sensitivity_sweep.png")

        tab("Export")
        scroll_to('[data-testid="stTabs"]')
        shot("09_export_tab.png")

        tab("Learn")
        scroll_to('[data-testid="stTabs"]')
        shot("10_learn_tab.png")

        browser.close()


if __name__ == "__main__":
    main()
