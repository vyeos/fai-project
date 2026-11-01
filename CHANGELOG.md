# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed
- Dashboard rebuilt as four pages (Try it, How it works, Experiments, Under the hood) with
  top navigation, no sidebar and no footer. "Try it" comes first: describe a road in plain
  terms and get the timing plan, per-car savings and side-by-side time-space diagrams.
- New light design system (IBM Plex, one accent blue for the optimized plan) shared by the
  Streamlit theme, the stylesheet and every chart; every page explains its numbers in
  plain language using one vocabulary.
- Search-trace charts and event table use plain-language event names.
- Minimum Streamlit version raised to 1.50 for the theming APIs.

### Fixed
- Invalid-scenario message no longer repeats "Invalid scenario configuration".
- Corridor drawings placed reverse-direction vehicles using the wrong visit order.

### Removed
- GitHub Actions workflow. Lint and tests now run locally before every push.

## [1.0.0] - 2026

### Added
- Corridor, intersection, vehicle, and timing-plan domain models with validated configuration.
- Deterministic traffic signal simulation (green-window model, red waiting, stop counting).
- Uncoordinated baseline (all offsets zero) and greedy one-way progression baseline.
- CSP optimizer: backtracking search, forward checking, branch-and-bound with the
  admissible h(s)=0 lower bound, configurable progression hard constraint, search
  statistics, and an inspectable search trace.
- Exhaustive-search verifier that independently checks optimality on small instances.
- Reproducible benchmark scenarios A-E with saved CSV/JSON results and summary.
- Streamlit dashboard: overview KPIs, scenario editor, corridor and timeline
  visualization, algorithm runs, comparison results, search-trace inspector,
  sensitivity analysis, CSV/JSON exports, and educational explanations.
- Automated pytest suite and GitHub Actions CI workflow.
- Academic deliverables: final report (DOCX/PDF), presentation (PPTX), speaker notes,
  demonstration guide, and viva preparation document.
