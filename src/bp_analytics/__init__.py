"""
bp_analytics — self-teaching vault: which notes get retrieved, which never,
what topic patterns emerge.

Responsibility
--------------
On every /recall, record a JSONL line (query scrubbed of credentials, list
of files surfaced, duration, vault-hit count). An aggregator rolls this up
into hot-notes / dead-notes / query-patterns reports.

Public API
----------
- record_recall(query, surfaced, duration_ms, vault_hits, research_fired)
- handle_hot_notes(handler_self, *, params)
- handle_dead_notes(handler_self, *, params)
- handle_query_patterns(handler_self, *, params)
- register_endpoints(gated_post, gated_get)

Storage
-------
- $XDG_STATE_HOME/brainpass/recall-log.jsonl (mode 0600)

Environment
-----------
- BP_ANALYTICS_ENABLED=true
- BP_PII_SCRUB_FILE=path-to-pii-patterns (optional)

Dependencies: stdlib only.

Failure modes
-------------
- Disk pressure: record_recall silently no-ops (§G11 safe_append_jsonl).
- Bad PII pattern: rejected at load via §G8 benchmark, logged, skipped.

Gotchas
-------
- Recall log retains query text (scrubbed). Set BP_ANALYTICS_ENABLED=false to disable.
- PII patterns are cached at import — librarian restart required after edits.
"""
from __future__ import annotations
import os

ENABLED = os.environ.get("BP_ANALYTICS_ENABLED", "true").lower() != "false"

from .recorder import record_recall, scrub_query
from .aggregator import hot_notes, dead_notes, query_patterns
from .handlers import handle_hot_notes, handle_dead_notes, handle_query_patterns


def register_endpoints(gated_post: set, gated_get: set) -> None:
    if not ENABLED:
        return
    gated_get.add("/analytics/hot-notes")
    gated_get.add("/analytics/dead-notes")
    gated_get.add("/analytics/query-patterns")
    try:
        from bp_routing import register_get
        register_get("/analytics/hot-notes", handle_hot_notes)
        register_get("/analytics/dead-notes", handle_dead_notes)
        register_get("/analytics/query-patterns", handle_query_patterns)
    except ImportError:
        pass


__all__ = [
    "record_recall", "scrub_query",
    "hot_notes", "dead_notes", "query_patterns",
    "handle_hot_notes", "handle_dead_notes", "handle_query_patterns",
    "register_endpoints", "ENABLED",
]
