"""KG test fixtures — date-literal-free.

Anything that needs an absolute date for synthetic input lives here so the
``src/kg/`` package itself stays clean for the no-hardcoded-date grep gate
(task #28). Fixtures derive timestamps from
``src.kg._calendar_adapter.get_default_t_start()`` so they track whatever
``ElectionCalendar`` reports as the active election window.
"""
from .synthetic_scenario import (  # noqa: F401
    SYNTHETIC_REGION_ID,
    SYNTHETIC_TIMESTEPS,
    make_synthetic_scenario,
)
