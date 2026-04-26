"""Page 7 — React EDA Explorer integration."""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import streamlit as st
import streamlit.components.v1 as components

_HERE = Path(__file__).resolve()
_DASH_ROOT = _HERE.parent.parent
if str(_DASH_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASH_ROOT))

from components.data_loader import render_sidebar  # noqa: E402

EDA_URL = "http://127.0.0.1:8234"
API_HEALTH_URL = "http://127.0.0.1:8235/api/health"

st.set_page_config(page_title="PolitiKAST · EDA Explorer", page_icon="📊", layout="wide")
render_sidebar("EDA Explorer")

st.title("EDA Explorer")
st.caption("React/Vite + FastAPI BFF 기반 Nemotron-Personas-Korea 탐색 UI")


def _reachable(url: str, timeout: float = 1.5) -> bool:
    try:
        with urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 400
    except (OSError, URLError):
        return False


frontend_ok = _reachable(EDA_URL)
backend_ok = _reachable(API_HEALTH_URL)

c1, c2 = st.columns(2)
c1.metric("React frontend :8234", "live" if frontend_ok else "down")
c2.metric("FastAPI BFF :8235", "live" if backend_ok else "down")

st.markdown(
    f"""
    - Frontend: [{EDA_URL}]({EDA_URL})
    - Ontology: [{EDA_URL}/ontology]({EDA_URL}/ontology)
    - Region compare: [{EDA_URL}/regions/compare]({EDA_URL}/regions/compare)
    - API health: [{API_HEALTH_URL}]({API_HEALTH_URL})
    """
)

if frontend_ok:
    components.iframe(f"{EDA_URL}/overview", height=860, scrolling=True)
else:
    st.warning(
        "EDA Explorer frontend is not reachable. Start it with "
        "`cd ui/eda-explorer/frontend && npm run dev -- --host 127.0.0.1 --port 8234`.",
        icon="⚠️",
    )

if not backend_ok:
    st.info(
        "FastAPI BFF is not reachable. Start it with "
        "`uv run --project ui/eda-explorer/backend uvicorn app:app --host 127.0.0.1 --port 8235`."
    )
