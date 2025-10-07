# dashboard/metrics.py
"""
Collect KPI dictionaries for the main dashboard.

Each provider returns:
    {"title": str, "value": Any, "icon": "🖼",           # mandatory
     "detail": Any | None, "href": str | None | ""}     # optional
"""
from typing import Callable, Dict, List

_PROVIDERS: list[Callable[[], Dict]] = []

def register(fn: Callable[[], Dict]):
    """Decorator – add function to the providers stack."""
    _PROVIDERS.append(fn)
    return fn        # so you can still unit-test the function

def gather() -> List[Dict]:
    """Return a list of KPI dicts – filters out providers that raise."""
    cards: list[Dict] = []
    for fn in _PROVIDERS:
        try:
            cards.append(fn() or {})
        except Exception:
            # keep a silent dashboard even if one provider misbehaves
            continue
    return cards

