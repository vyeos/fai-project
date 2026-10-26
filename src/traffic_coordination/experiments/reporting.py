"""Summary rendering and figure generation for benchmark results."""

from __future__ import annotations

import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless rendering for CI and scripted runs
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ALGO_LABELS = {
    "uncoordinated": "Uncoordinated",
    "greedy": "Greedy one-way",
    "csp": "CSP + FC + B&B",
}
ALGO_ORDER = ["uncoordinated", "greedy", "csp"]
ALGO_COLORS = {"uncoordinated": "#c44e52", "greedy": "#dd8452", "csp": "#4c72b0"}

MAIN_SCENARIOS = ["A", "B", "C", "D", "E"]

__all__ = ["render_summary", "build_figures"]


def _markdown_table(subset: pd.DataFrame) -> str:
    """Render a DataFrame as a GitHub-compatible markdown table (no extra deps)."""
    headers = [str(col) for col in subset.columns]
    rows = [
        ["" if value is None or value != value else str(value) for value in record]
        for record in subset.itertuples(index=False, name=None)
    ]
    parts = ["| " + " | ".join(headers) + " |", "|" + "|".join([" --- "] * len(headers)) + "|"]
    parts.extend("| " + " | ".join(r) + " |" for r in rows)
    return "\n".join(parts)


def _frame_main(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[frame["scenario"].isin(MAIN_SCENARIOS)].copy()


def render_summary(frame: pd.DataFrame, metadata: dict[str, object]) -> str:
    """Render ``experiments/results/summary.md`` from actual results."""
    lines: list[str] = []
    lines.append("# Benchmark Summary")
    lines.append("")
    lines.append(f"*Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}.*")
    lines.append(
        "All values are measured from deterministic simulations of documented "
        "simplifying assumptions; they are **not** field measurements and not the "
        "report's illustrative figures."
    )
    lines.append("")
    lines.append(
        "**Objective:** J = alpha*W + beta*S (defaults alpha=1, beta=2; "
        "per-row alpha/beta recorded in the CSV)."
    )
    lines.append("")

    for table, title in (
        (MAIN_SCENARIOS, "Main scenarios (report benchmark matrix)"),
        (None, "Sensitivity scenarios"),
    ):
        if table is None:
            subset = frame[~frame["scenario"].isin(MAIN_SCENARIOS)].copy()
        else:
            subset = _frame_main(frame)
        if subset.empty:
            continue
        lines.append(f"## {title}")
        lines.append("")
        cols = [
            "scenario",
            "algorithm",
            "total_waiting_time_s",
            "average_waiting_time_s",
            "total_stops",
            "objective",
            "search_time_s",
            "nodes_expanded",
            "complete_assignments_evaluated",
            "forward_check_removals",
            "branch_bound_prunes",
            "status",
            "plan_offsets",
        ]
        subset = subset[cols]
        lines.append(_markdown_table(subset))
        lines.append("")

    verifications = [
        meta
        for name, meta in (metadata.get("scenarios", {}) or {}).items()  # type: ignore[union-attr]
        if isinstance(meta, dict) and meta.get("verification", {}).get("performed")  # type: ignore[union-attr]
    ]
    if verifications:
        lines.append("## Exhaustive verification (independent brute force)")
        lines.append("")
        for meta in verifications:  # type: ignore[union-attr]
            ver = meta["verification"]  # type: ignore[index]
            name = meta.get("scenario", "?")  # type: ignore[attr-defined]
            if not ver.get("completed", False):
                lines.append(
                    f"- **{name}**: verification did not complete within budget "
                    f"({ver.get('plans_considered', 0)}); optimality not yet proven."
                )
            else:
                lines.append(
                    f"- **{name}**: brute force over {ver['feasible_plans']} feasible plans "
                    f"(of {ver['plans_considered']}), CSP matches best "
                    f"(J={ver['best_objective']}): {ver['csp_matches_brute_force']}."
                )
        lines.append("")

    skipped = [
        (name, meta)
        for name, meta in (metadata.get("scenarios", {}) or {}).items()  # type: ignore[union-attr]
        if isinstance(meta, dict) and not meta.get("verification", {}).get("performed")  # type: ignore[union-attr]
    ]
    if skipped:
        lines.append("## Honestly-incomplete items")
        lines.append("")
        for name, meta in skipped:
            space = meta["verification"].get("space_size", "?")  # type: ignore[index]
            lines.append(
                f"- **{name}**: exhaustive verification skipped (search space {space} plans). "
                "The CSP search itself completed within its hard-constraint space."
            )
        lines.append("")
    return "\n".join(lines)


def build_figures(frame: pd.DataFrame, out_dir: Path) -> list[Path]:
    """Generate the six required benchmark figures from measured data."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    main = _frame_main(frame)

    def _group_bar(metric: str, ylabel: str, fname: str, title: str) -> Path | None:
        if main.empty:
            return None
        pivot = main.pivot(index="scenario", columns="algorithm", values=metric)
        pivot.columns = [ALGO_LABELS.get(c, c) for c in pivot.columns]
        fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
        pivot.plot(kind="bar", ax=ax, color=[ALGO_COLORS[key] for key in ALGO_ORDER])
        ax.set_title(title)
        ax.set_xlabel("Scenario")
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        path = out_dir / fname
        fig.savefig(path)
        plt.close(fig)
        paths.append(path)
        return path

    _group_bar(
        "total_waiting_time_s",
        "Total waiting time (s)",
        "fig1_waiting_by_scenario.png",
        "Total simulated waiting time by algorithm",
    )
    _group_bar(
        "total_stops", "Stops", "fig2_stops_by_scenario.png", "Total simulated stops by algorithm"
    )

    # 3+4: scalability with corridor size (scenarios A, B, C by construction)
    size_frame = frame[frame["scenario"].isin(["A", "B", "C", "F2", "G1"])].copy()
    if not size_frame.empty:
        csp = size_frame[size_frame["algorithm"] == "csp"].copy()
        csp = csp.sort_values("n_intersections")
        fig, axes = plt.subplots(1, 2, figsize=(11, 4), dpi=150)
        axes[0].plot(
            csp["n_intersections"],
            csp["search_time_s"],
            "o-",
            color=ALGO_COLORS["csp"],
            label="CSP search time",
        )
        for algo in ("uncoordinated", "greedy"):
            g = size_frame[size_frame["algorithm"] == algo].sort_values("n_intersections")
            axes[0].plot(
                g["n_intersections"],
                g["search_time_s"],
                "s--",
                color=ALGO_COLORS[algo],
                label=ALGO_LABELS[algo],
            )
        axes[0].set_xlabel("Corridor size N (intersections)")
        axes[0].set_ylabel("Runtime (s)")
        axes[0].set_title("Runtime vs corridor size")
        axes[0].legend()
        axes[0].grid(alpha=0.3)
        axes[1].plot(
            csp["n_intersections"],
            csp["nodes_expanded"],
            "o-",
            color=ALGO_COLORS["csp"],
            label="CSP nodes expanded",
        )
        axes[1].plot(
            csp["n_intersections"],
            csp["complete_assignments_evaluated"],
            "^-",
            color="#55a868",
            label="Complete plans simulated",
        )
        axes[1].plot(
            csp["n_intersections"], csp["search_space_size"], "k--", label="Raw space D^(N-1)"
        )
        axes[1].set_yscale("log")
        axes[1].set_xlabel("Corridor size N (intersections)")
        axes[1].set_ylabel("Count (log)")
        axes[1].set_title("Search effort vs corridor size (CSP)")
        axes[1].legend()
        axes[1].grid(alpha=0.3)
        fig.tight_layout()
        path = out_dir / "fig3_runtime_nodes_vs_size.png"
        fig.savefig(path)
        plt.close(fig)
        paths.append(path)

    # 5: demand sensitivity (F1, F2, F3)
    demand = frame[frame["scenario"].isin(["F1", "F2", "F3"])].copy()
    if not demand.empty:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4), dpi=150)
        pivot_w = demand.pivot(index="scenario", columns="algorithm", values="total_waiting_time_s")
        pivot_s = demand.pivot(index="scenario", columns="algorithm", values="total_stops")
        for ax, pv, ttl, yl in (
            (axes[0], pivot_w, "Total waiting time vs demand", "Waiting (s)"),
            (axes[1], pivot_s, "Total stops vs demand", "Stops"),
        ):
            pv.columns = [ALGO_LABELS.get(c, c) for c in pv.columns]
            pv.plot(kind="bar", ax=ax, color=[ALGO_COLORS[k] for k in ALGO_ORDER])
            ax.set_title(ttl)
            ax.set_xlabel("Demand scenario (F1 low, F2 medium, F3 high)")
            ax.set_ylabel(yl)
            ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        path = out_dir / "fig5_demand_sensitivity.png"
        fig.savefig(path)
        plt.close(fig)
        paths.append(path)

    # 6: resolution sensitivity (G1 vs G2, matched constraint)
    res = frame[frame["scenario"].isin(["G1", "G2"])].copy()
    if not res.empty and len(res["scenario"].unique()) == 2:
        fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
        pivot = res.pivot(index="scenario", columns="algorithm", values="total_waiting_time_s")
        pivot.columns = [ALGO_LABELS.get(c, c) for c in pivot.columns]
        pivot.plot(kind="bar", ax=ax, color=[ALGO_COLORS[k] for k in ALGO_ORDER])
        ax.set_title("Offset resolution sensitivity (10 s progression tolerance)")
        ax.set_xlabel("Scenario (G1 = 5 s, G2 = 1 s)")
        ax.set_ylabel("Total waiting time (s)")
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        path = out_dir / "fig6_resolution_sensitivity.png"
        fig.savefig(path)
        plt.close(fig)
        paths.append(path)

    # Sensitivity: nominal speed (H1/B/H2) and objective weights (J1/B/J2)
    speed = frame[frame["scenario"].isin(["H1", "B", "H2"])]
    if not speed.empty:
        fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
        pivot = speed.pivot(index="scenario", columns="algorithm", values="total_waiting_time_s")
        pivot.columns = [ALGO_LABELS.get(c, c) for c in pivot.columns]
        pivot.plot(kind="bar", ax=ax, color=[ALGO_COLORS[k] for k in ALGO_ORDER])
        ax.set_title("Nominal speed sensitivity (B = 40 km/h)")
        ax.set_xlabel("Scenario (H1 = 30 km/h, B = 40 km/h, H2 = 50 km/h)")
        ax.set_ylabel("Total waiting time (s)")
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        path = out_dir / "fig7_speed_sensitivity.png"
        fig.savefig(path)
        plt.close(fig)
        paths.append(path)

    weights = frame[frame["scenario"].isin(["J1", "B", "J2"])]
    if not weights.empty:
        fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
        pivot = weights.pivot(index="scenario", columns="algorithm", values="total_stops")
        pivot.columns = [ALGO_LABELS.get(c, c) for c in pivot.columns]
        pivot.plot(kind="bar", ax=ax, color=[ALGO_COLORS[k] for k in ALGO_ORDER])
        ax.set_title("Objective-weight sensitivity (stops metric; J1 beta=0, B beta=2, J2 beta=4)")
        ax.set_xlabel("Scenario")
        ax.set_ylabel("Total stops")
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        path = out_dir / "fig8_weights_sensitivity.png"
        fig.savefig(path)
        plt.close(fig)
        paths.append(path)

    return paths
