"""Streamlit dashboard for classical AI-based traffic signal coordination.

Run from the repository root:

    python -m streamlit run app.py

Four pages, in reading order: try the model on a road you describe, learn how
it works, compare strategies across experiments, and inspect the search. All
metrics come from the deterministic simplified simulator documented in the
report; nothing here is a field measurement.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from a source checkout without an editable install.
_SRC = Path(__file__).resolve().parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st  # noqa: E402

from traffic_coordination import ui_theme as ui  # noqa: E402
from traffic_coordination.dashboard import (  # noqa: E402
    common,
    experiments,
    how_it_works,
    try_it,
    under_the_hood,
)

st.set_page_config(
    page_title="Traffic Light Timing",
    page_icon=":material/traffic:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.html(ui.GLOBAL_CSS)

common.PAGES.update(
    {
        "try": st.Page(try_it.render, title="Try it", icon=":material/tune:", url_path="try", default=True),
        "how": st.Page(how_it_works.render, title="How it works", icon=":material/menu_book:", url_path="how-it-works"),
        "experiments": st.Page(experiments.render, title="Experiments", icon=":material/science:", url_path="experiments"),
        "hood": st.Page(under_the_hood.render, title="Under the hood", icon=":material/data_object:", url_path="under-the-hood"),
    }
)
st.navigation(list(common.PAGES.values()), position="top").run()
