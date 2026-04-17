"""
bp_temporal — decay scoring, /changed, /timeline, cross-time staleness.

Responsibility
--------------
Recent notes outrank old notes. Users can ask "what changed since X" and
"show me the timeline of topic Y" — the latter surfaces contradictions
between old and new claims.

Public API
----------
- decay_score(mtime_unix, now_unix, half_life_days) -> float
- apply_decay(ranked_results) -> list[ranked_result]
- handle_changed(handler_self, *, params) -> None
- handle_timeline(handler_self, *, params) -> None
- register_endpoints(gated_post, gated_get) -> None

Storage: none (reads vault directly).

Environment
-----------
- BP_TEMPORAL_ENABLED=true
- BP_TEMPORAL_HALF_LIFE_DAYS=30
- BP_TEMPORAL_STALENESS=true

Dependencies: stdlib only.

Failure modes
-------------
- Vault path missing: endpoints return empty lists.
- Individual file read errors: skipped, not fatal.

Gotchas
-------
- Decay multiplies the existing RRF score — if the librarian isn't using
  RRF yet, apply_decay is a no-op.
"""
from __future__ import annotations
import os

ENABLED = os.environ.get("BP_TEMPORAL_ENABLED", "true").lower() != "false"
HALF_LIFE_DAYS = float(os.environ.get("BP_TEMPORAL_HALF_LIFE_DAYS", "30"))
STALENESS_ENABLED = os.environ.get("BP_TEMPORAL_STALENESS", "true").lower() != "false"

from .decay import decay_score, apply_decay
from .handlers import handle_changed, handle_timeline


def register_endpoints(gated_post: set, gated_get: set) -> None:
    if not ENABLED:
        return
    gated_get.add("/changed")
    gated_get.add("/timeline")
    try:
        from bp_routing import register_get
        register_get("/changed", handle_changed)
        register_get("/timeline", handle_timeline)
    except ImportError:
        pass


__all__ = [
    "decay_score", "apply_decay",
    "handle_changed", "handle_timeline",
    "register_endpoints",
    "ENABLED", "HALF_LIFE_DAYS", "STALENESS_ENABLED",
]
