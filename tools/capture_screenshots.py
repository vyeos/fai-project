"""Recapture the dashboard screenshots in docs/screenshots/.

Start the dashboard first (``python -m streamlit run app.py --server.port 8599``),
then, from any environment with Playwright installed (``pip install playwright``;
it is not a project dependency):

    python tools/capture_screenshots.py docs/screenshots [http://localhost:8599]

It drives the locally installed Microsoft Edge headlessly at 1440x960, scale 1.5,
visits the four pages on the default road, runs one traffic sweep on the
Experiments page and saves one PNG per view.
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1])
URL = (sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8599").rstrip("/")
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 960}, device_scale_factor=1.5)

        def settle(ms: int = 1600) -> None:
            page.wait_for_timeout(ms)

        def visit(path: str, ready: str) -> None:
            # Client-side navigation keeps the session (and the default run).
            page.get_by_role("link", name=path, exact=True).first.click()
            page.wait_for_selector(ready, timeout=120_000)
            page.evaluate("document.fonts.ready")
            settle(2200)

        def to_heading(text: str, block: str = "start") -> None:
            page.evaluate(
                "([t, b]) => [...document.querySelectorAll('h2, h3')]"
                ".find(h => h.innerText.trim() === t).scrollIntoView({block: b})",
                [text, block],
            )
            settle(900)

        def to_top() -> None:
            page.evaluate("window.scrollTo(0, 0)")
            settle(700)

        def shot(name: str) -> None:
            page.mouse.move(5, 5)
            page.screenshot(path=str(OUT / name))
            print("saved", name)

        page.goto(URL)
        page.wait_for_selector(".ui-summary", timeout=120_000)
        page.evaluate("document.fonts.ready")
        settle(2500)

        # Page 1: Try it
        shot("01_try_it_form.png")
        to_heading("When each light turns green")
        shot("02_try_it_plan.png")
        to_heading("See the difference")
        page.wait_for_selector(".js-plotly-plot", state="attached")
        settle(1500)
        shot("03_try_it_time_space.png")
        to_heading("Three ways to time the lights")
        shot("04_try_it_strategies.png")

        # Page 2: How it works
        visit("How it works", ".ui-terms")
        to_top()
        shot("05_how_problem.png")
        to_heading("Words used on this site")
        shot("06_how_terms.png")
        to_heading("How a plan is scored")
        shot("07_how_simulator.png")
        to_heading("How the optimized search works")
        shot("08_how_search.png")

        # Page 3: Experiments
        visit("Experiments", '[data-testid="stTable"], [data-testid="stDataFrame"], table')
        to_top()
        shot("09_experiments_roads.png")
        page.get_by_role("button", name="Run comparison").click()
        page.wait_for_selector(".ui-callout", timeout=180_000)
        settle(2500)
        to_heading("What changes the result?")
        shot("10_experiments_sweep.png")

        # Page 4: Under the hood
        visit("Under the hood", 'h2:has-text("Was the answer double-checked?")')
        to_top()
        shot("11_hood_check.png")
        to_heading("How much searching it took")
        shot("12_hood_effort.png")
        to_heading("The search, step by step")
        settle(1200)
        shot("13_hood_trace.png")

        browser.close()


if __name__ == "__main__":
    main()
