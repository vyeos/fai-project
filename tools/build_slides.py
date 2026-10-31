"""Build the ~13-slide project presentation as PPTX from real artefacts.

Run from the repository root:

    python -X utf8 tools/build_slides.py

Output: deliverables/final_slides.pptx

Every number is measured (experiments/results/summary.md); screenshots come
from a verified live dashboard session; unknown academic fields remain
placeholders. Speaker notes are attached to each slide.
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "deliverables"
OUT.mkdir(exist_ok=True)

ACCENT = RGBColor(0x1F, 0x4E, 0x79)
MUTED = RGBColor(0x59, 0x59, 0x59)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

S_W, S_H = Inches(13.333), Inches(7.5)


def new_deck() -> Presentation:
    """Create the presentation shell."""
    deck = Presentation()
    deck.slide_width = S_W
    deck.slide_height = S_H
    return deck


def add_content_slide(deck: Presentation, title: str, bullets: list[str]) -> None:
    """Title + bullet body slide with notes."""
    slide = deck.slides.add_slide(deck.slide_layouts[1])
    slide.shapes.title.text = title
    body = slide.placeholders[1].text_frame
    body.clear()
    for index, text in enumerate(bullets):
        paragraph = body.paragraphs[0] if index == 0 else body.add_paragraph()
        paragraph.text = text
        paragraph.font.size = Pt(16)
        paragraph.font.color.rgb = RGBColor(0x26, 0x26, 0x26)
    return slide


def add_picture_slide(deck: Presentation, title: str, image: str, subtitle: str = "") -> None:
    """Title + full-width picture slide; picture keeps aspect via height."""
    slide = deck.slides.add_slide(deck.slide_layouts[5])
    slide.shapes.title.text = title
    path = REPO / image
    if not path.exists():
        raise FileNotFoundError(f"missing image: {path}")
    slide.shapes.add_picture(str(path), Inches(0.55), Inches(1.25), height=Inches(5.7))
    if subtitle:
        box = slide.shapes.add_textbox(Inches(0.55), Inches(6.95), S_W - Inches(1.1), Inches(0.45))
        frame = box.text_frame
        frame.text = subtitle
        frame.paragraphs[0].font.size = Pt(11)
        frame.paragraphs[0].font.color.rgb = MUTED
        frame.paragraphs[0].font.italic = True


def add_table_slide(deck: Presentation, title: str, headers: list[str], rows: list[list[str]], notes: str) -> None:
    """Title + styled result table slide."""
    slide = deck.slides.add_slide(deck.slide_layouts[5])
    slide.shapes.title.text = title
    table = slide.shapes.add_table(
        1 + len(rows), len(headers), Inches(0.55), Inches(1.5),
        S_W - Inches(1.1), Inches(1.0 + 0.62 * len(rows)),
    ).table
    for col, header in enumerate(headers):
        cell = table.cell(0, col)
        cell.text = header
        run = cell.text_frame.paragraphs[0].runs[0]
        run.font.bold = True
        run.font.size = Pt(14)
        run.font.color.rgb = WHITE
        cell.fill.solid()
        cell.fill.fore_color.rgb = ACCENT
    for row_idx, row in enumerate(rows, start=1):
        for col, value in enumerate(row):
            cell = table.cell(row_idx, col)
            cell.text = value
            run = cell.text_frame.paragraphs[0].runs[0]
            run.font.size = Pt(13)
    _set_notes(slide, notes)


def _set_notes(slide, notes: str) -> None:
    """Attach speaker notes text to a slide."""
    slide.notes_slide.notes_text_frame.text = notes


def build() -> Presentation:
    """Assemble the deck."""
    deck = new_deck()

    # 1. Title
    slide = deck.slides.add_slide(deck.slide_layouts[0])
    slide.shapes.title.text = "Classical AI-Based Traffic Signal Coordination"
    slide.placeholders[1].text = (
        "ECSCT24301 — Foundation of AI · Applied AI project · Adani University, AY 2026–27\n"
        "Rudra Patel (2410111118) · Pruthvi Navadiya (2410111071)\n"
        "Supervisor: [placeholder] · Date: [placeholder]"
    )
    _set_notes(slide, (
        "Good morning. We coordinate the green windows of N signalized intersections on an arterial "
        "corridor using classical AI search. Everything you will see was measured inside a deterministic, "
        "reproducible simulation — no invented numbers, and honestly-labelled placeholders where course "
        "information was not available."
    ))

    # 2. The problem
    add_content_slide(deck, "The problem", [
        "Independently-timed signals waste platoon progress: arrivals meet red, vehicles stop and wait",
        "Coordination idea: shift each signal's green window in time (the offset Oi) so greens 'pass' platoons along",
        "Offsets interact around the cycle — choosing all of them is a discrete, simulation-evaluated search problem",
        "Objective: J = alpha*W + beta*S (W total waiting, S total stops; defaults alpha=1, beta=2)",
        "Why classical AI: combinatorial state space (|D|^(N-1)), hard constraints, complete-search machinery fits exactly",
    ])
    _notes_last(deck, (
        "Frame it as a textbook CSP instantiated on a corridor. Stress that the simulator is the single "
        "source of truth shared by all three algorithms — comparisons are apples-to-apples by construction."
    ))

    # 3. Model and assumptions
    add_content_slide(deck, "Simulation model (documented simplifications)", [
        "N intersections, common cycle C=60 s, coordinated green G=30 s, offsets on a 5 s grid {|D|=12}",
        "Green iff ((t - Oi) mod C) < G; speed constant at 40 km/h; tau ~ 36 s per 400 m link",
        "Vehicles: seeded RNG platoon/uniform departures, both directions, no queues or capacity limits",
        "One stop per red arrival; half-open windows; deterministic everything (bit-for-bit reproducible)",
        "Not a traffic-engineering design tool — a controlled test bed for search algorithms",
    ])
    _notes_last(deck, (
        "Own the limitations proactively: constant speeds and no queues. Then point out the pay-off — "
        "determinism makes every reported number reproducible, and one shared simulator isolates the plan's effect."
    ))

    # 4. CSP formulation
    add_content_slide(deck, "CSP formulation", [
        "Variables: O2..ON (O1 = 0 fixes the temporal reference; only differences mod C matter)",
        "Domains: {0, 5, ..., 55} — 12 values per variable; space = 12^4 = 20,736 plans for N=5",
        "Hard constraints: domain bounds; O1=0; optional progression tolerance rho=10 s on adjacent pairs",
        "Soft objective: J = alpha*W + beta*S via the simulator",
        "Tolerance is a design lever: rho=None makes it vacuous (FC removes nothing); rho=10 s gives real pruning",
    ])
    _notes_last(deck, (
        "Show the honesty lever: with no tolerance the search becomes a structured exhaustive enumeration "
        "of 20,736 plans; with rho=10 s scenario C's 2.99M raw plans collapse to 4,096 evaluated plans."
    ))

    # 5. The three algorithms
    add_content_slide(deck, "Three comparable strategies", [
        "Uncoordinated: all offsets 0 — one deterministic plan; reproduces the report's illustrative row exactly (3,460 s / 160 stops)",
        "Greedy progression: O(i+1) = round(Oi + tau mod C) — one pass, forward direction only, no search",
        "CSP optimizer: backtracking + forward checking + branch and bound, budget-bounded and instrumented",
        "All three scored by the SAME simulator on identical generated demand",
        "Statuses are honest: 'optimality proven' only after a complete search; budgets yield 'best-so-far, unproven'",
    ])
    _notes_last(deck, (
        "Greedy is not a strawman — it wins on light demand and forward-only traffic, but can actively hurt "
        "the reverse direction (scenario H1: greedy J=2246 vs uncoordinated 1828). The CSP fixes both directions."
    ))

    # 6. Search machinery + honesty
    add_content_slide(deck, "Search machinery — and honest counters", [
        "Forward checking: delete next variable's values violating the pairwise tolerance (chain graph: one neighbour suffices)",
        "Measured: scenario C removed 10,920 values; scenario G2 (1 s grid) removed 379,236",
        "Branch and bound: incumbent J and an admissible lower bound h(s)=0 — admissible but weak",
        "Honest result: zero prunes in every run; the counter reports the truth instead of inflating claims",
        "Time budget and evaluation cap are hard stops; expiry reports 'incomplete' verbatim",
    ])
    _notes_last(deck, (
        "If asked 'why is B&B useless here?': h=0 is admissible and consistent, so correctness holds, but 0 "
        "never beats a real incumbent — pruning nothing. A real lower-bound function is future work we name."
    ))

    # 7. Verification methodology
    add_content_slide(deck, "Independent verification", [
        "A second, independently-written module brute-forces the hard-constraint feasible set with the same simulator",
        "Wherever it runs, its best plan must match the CSP objective (agreement within 1e-9)",
        "Verified on 12 of 14 scenarios: A (144 plans), B, D, F1-F3, H1, H2, J1, J2 (20,736), G1 (256), G2 (194,481)",
        "Skipped honestly: C (2,985,984 raw plans) and E (12,960,000) — too large for the 60 s verification budget",
        "Principle: never claim optimality that was neither search-derived nor independently verified",
    ])
    _notes_last(deck, (
        "The verifier is not the solver's own bookkeeping — it's independent code cross-checking the optimum. "
        "Skips are recorded with space sizes stated, not hidden."
    ))

    # 8. Dashboard tour (screenshot)
    add_picture_slide(
        deck, "Dashboard — nine tabs, live-verified",
        "docs/screenshots/01_overview_last_run.png",
        "Live session: CSP proven optimal, 83.7% improvement banner, verification alert over 256 feasible plans (J = 618.00).",
    )
    _notes_last(deck, (
        "Demo flow: load scenario B, run all algorithms, show the banner; the corridor tab animates platoons "
        "at t=57 s; the search inspector shows the counters; sensitivity runs a live sweep; exports give CSV/JSON."
    ))

    # 9. Search inspector (screenshot)
    add_picture_slide(
        deck, "CSP search-trace inspection",
        "docs/screenshots/06b_search_trace_charts.png",
        "Event histograms and depth charts from the retained trace; aggregate counters cover the entire search.",
    )
    _notes_last(deck, (
        "The trace is a first-events window; the histogram counts everything. This separation is stated in the UI "
        "so no one mistakes the windowed events for the whole search."
    ))

    # 10. Headline measured results
    add_table_slide(
        deck, "Measured results (main scenarios)",
        ["Scenario", "Uncoord.", "Greedy", "CSP", "CSP gain", "CSP status"],
        [
            ["A (3 int, low)", "762", "140", "140", "81.6%", "proven + verified"],
            ["B (5 int, medium)", "3780", "830", "618", "83.7%", "proven + verified (20,736)"],
            ["C (7 int, rho=10)", "5860", "1610", "674", "88.5%", "proved in tolerant space; raw-space verify skipped"],
            ["D (5 int, high)", "10406", "2525", "2078", "80.0%", "proven + verified (20,736)"],
            ["E (1 s grid)", "3780", "850", "605", "84.0%", "proved in tolerant space; raw-space verify skipped"],
        ],
        "All values measured (experiments/results/summary.md, alpha=1 beta=2). Improvement = (J_unc - J_csp)/J_unc. "
        "Quote scenario B end-to-end if challenged: plan O=(0,40,5,40,15), 20,736 plans evaluated, verification agrees at J=618.",
    )

    # 11. Search statistics table
    add_table_slide(
        deck, "Search statistics — pruning that is real, counters that are true",
        ["Scenario", "Plans evaluated", "Nodes", "FC removals", "B&B prunes", "Time (s)"],
        [
            ["A", "144 / 144", "13", "0", "0", "0.005"],
            ["B", "20,736 / 20,736", "1885", "0", "0", "1.43"],
            ["C", "4,096 (of 2,985,984 raw)", "1365", "10,920", "0", "0.35"],
            ["E", "194,481 (tolerant)", "9724", "379,236", "0", "12.40"],
        ],
        "FC eliminations are real exactly where the tolerance constraint exists; zeros elsewhere are stated as zeros. "
        "Scenario E's resolution switch multiplied runtime ~9x — the price of a 1 s grid.",
    )

    # 12. Sensitivity figure
    add_picture_slide(
        deck, "Sensitivity: demand and resolution dominate outcomes",
        "experiments/figures/fig5_demand_sensitivity.png",
        "F-family demand sweep; also measured: H1 (greedy worse than uncoordinated), H2 (near-perfect progression, J=24 vs 1008.8), J-family (same plan optimal at beta=2 and beta=5).",
    )
    _notes_last(deck, (
        "Sensitivity conclusions: (i) CSP benefit persists across demand; (ii) resolution is expensive but rewarding; "
        "(iii) the chosen plan is weight-robust because it improves W and S simultaneously."
    ))

    # 13. Limitations, future work, wrap-up
    add_content_slide(deck, "Limitations, future work, takeaways", [
        "Limitations: no queues/capacity, one coordinated phase, synthetic demand, h(s)=0 prunes nothing",
        "Future: informative admissible bound; queueing model; min-conflicts for large N; multi-phase timing; field validation",
        "Engineering: 76 passing tests, ruff-clean, lint + tests run locally before every push, one-command reproducible benchmarks",
        "Deliverables: report DOCX+PDF, this deck + speaker notes, demo guide, 42-question viva prep, 15 live-verified screenshots",
        "Takeaway: formulation honest, search complete or honestly incomplete, optimality verified wherever feasible",
    ])
    _notes_last(deck, (
        "Close on the integrity angle: every number traces to a results file, every limitation is documented, "
        "and every optimality claim carries independent verification or an explicit skip."
    ))

    return deck


def _notes_last(deck: Presentation, notes: str) -> None:
    """Attach notes to the most recently added slide."""
    _set_notes(deck.slides[-1], notes)


def main() -> None:
    """Build and save the PPTX."""
    deck = build()
    output = OUT / "final_slides.pptx"
    deck.save(output)
    print(f"saved {output}, {len(deck.slides._sldIdLst)} slides")


if __name__ == "__main__":
    main()
