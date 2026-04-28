"""Per-source adapter modules.

Each adapter exports `get_adapter() -> SourceAdapter`. Implementations live
in sibling files; this package is intentionally bare so `importlib` lookups
work without side effects.
"""
