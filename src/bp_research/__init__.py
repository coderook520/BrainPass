"""
bp_research — auto-research: when the vault is empty on a topic, fetch
from open web + whitelist, synthesize with LLM, enqueue findings via
write-back.

Responsibility
--------------
Close the cold-start problem. Empty vault + new question = research the
open web + trusted whitelist, synthesize an answer with citations, draft
a note that lands in writeback queue for user approval. Next time the
topic comes up, it's already in the vault.

Public API
----------
- should_fire(vault_hits) -> bool
- run_inline_or_background(query, vault_hits) -> dict | None
- submit_background(fn, *args) -> None  (used by bp_writeback async extractor)
- module_ready() -> bool  (False when bs4 missing → disables research)

Storage
-------
- $XDG_STATE_HOME/brainpass/research-cost.jsonl (cost tracking)
- $XDG_STATE_HOME/brainpass/research-error.jsonl (error log)
- $XDG_STATE_HOME/brainpass/research-cache.sqlite (content-hash replay cache)

Environment
-----------
- BP_AUTORESEARCH_ENABLED=true            master switch (DEFAULT ON)
- BP_AUTORESEARCH_MODE=smart              smart | always | off | explicit
- BP_AUTORESEARCH_THRESHOLD=2             min vault hits to suppress
- BP_AUTORESEARCH_WHITELIST_ONLY=false
- BP_AUTORESEARCH_WHITELIST=wikipedia.org,arxiv.org,duckduckgo.com
- BP_AUTORESEARCH_MAX_BYTES_PER_FETCH=204800
- BP_AUTORESEARCH_MAX_BYTES_TOTAL=614400
- BP_AUTORESEARCH_INLINE_BUDGET_SECONDS=3.0
- BP_AUTORESEARCH_TIMEOUT_TOTAL=30
- BP_AUTORESEARCH_WARN_DAILY_USD=5.00
- BP_AUTORESEARCH_HARD_CAP_USD=             (unset = uncapped)

Dependencies
------------
- stdlib only (http.client, ssl, socket, ipaddress)
- beautifulsoup4 SOFT-REQUIRED. Without it, module_ready() returns False,
  and should_fire() returns False, disabling auto-research cleanly.

Failure modes (all non-fatal)
-----------------------------
- DNS timeout / unreachable → TimeoutError, caught, returns None.
- Private IP in record set → ValueError, caught, returns None.
- LLM provider 429/5xx/malformed → caught in _do_research_safe, returns
  shape-stable error dict; /recall never raises from research.
- Disk full on cost log → safe_append_jsonl silently skips.
- Executor queue saturated → run_inline_or_background returns None.
"""
from __future__ import annotations
import concurrent.futures
import logging
import os
import threading

ENABLED = os.environ.get("BP_AUTORESEARCH_ENABLED", "true").lower() != "false"
MODE = os.environ.get("BP_AUTORESEARCH_MODE", "smart").lower()
THRESHOLD = int(os.environ.get("BP_AUTORESEARCH_THRESHOLD", "2"))
WHITELIST_ONLY = os.environ.get("BP_AUTORESEARCH_WHITELIST_ONLY", "false").lower() == "true"
WHITELIST = tuple(
    s.strip() for s in os.environ.get(
        "BP_AUTORESEARCH_WHITELIST",
        "wikipedia.org,arxiv.org,duckduckgo.com",
    ).split(",") if s.strip()
)
MAX_BYTES_PER_FETCH = int(os.environ.get("BP_AUTORESEARCH_MAX_BYTES_PER_FETCH", "204800"))
MAX_BYTES_TOTAL = int(os.environ.get("BP_AUTORESEARCH_MAX_BYTES_TOTAL", "614400"))
INLINE_BUDGET_S = float(os.environ.get("BP_AUTORESEARCH_INLINE_BUDGET_SECONDS", "3.0"))
TIMEOUT_TOTAL = float(os.environ.get("BP_AUTORESEARCH_TIMEOUT_TOTAL", "30"))
WARN_DAILY_USD = float(os.environ.get("BP_AUTORESEARCH_WARN_DAILY_USD", "5.00"))
HARD_CAP_USD = float(os.environ.get("BP_AUTORESEARCH_HARD_CAP_USD", "0")) or None
MAX_QUEUE_DEPTH = 10

_log = logging.getLogger("bp_research")

_HAS_BS4 = False
try:
    import bs4  # noqa: F401
    _HAS_BS4 = True
except ImportError:
    pass

_EXECUTOR: concurrent.futures.ThreadPoolExecutor = (
    concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="bp-research")
)
_INFLIGHT: dict[str, concurrent.futures.Future] = {}
_INFLIGHT_LOCK = threading.Lock()


def module_ready() -> bool:
    if not ENABLED:
        return False
    if not _HAS_BS4:
        _log.warning(
            "beautifulsoup4 not installed — auto-research disabled. "
            "Install with: pip install --user beautifulsoup4"
        )
        return False
    return True


def submit_background(fn, *args, **kwargs) -> concurrent.futures.Future | None:
    """Fire-and-forget task (used by bp_writeback)."""
    try:
        if _EXECUTOR._work_queue.qsize() >= MAX_QUEUE_DEPTH:
            return None
        return _EXECUTOR.submit(fn, *args, **kwargs)
    except RuntimeError:
        return None


def shutdown(wait: bool = True, timeout: float = 5.0) -> None:
    """Called by librarian's SIGTERM/SIGINT handler (§G4)."""
    try:
        _EXECUTOR.shutdown(wait=wait, cancel_futures=True)
    except Exception:
        pass


from .trigger import should_fire, run_inline_or_background  # noqa: E402


def register_endpoints(gated_post: set, gated_get: set) -> None:
    # bp_research does not add new endpoints — it's invoked inline from /recall.
    # (A manual /research endpoint may be added in a follow-up PR.)
    pass


__all__ = [
    "should_fire", "run_inline_or_background", "submit_background",
    "module_ready", "shutdown", "register_endpoints",
    "ENABLED", "MODE", "THRESHOLD", "WHITELIST_ONLY", "WHITELIST",
    "INLINE_BUDGET_S", "TIMEOUT_TOTAL", "MAX_BYTES_PER_FETCH", "MAX_BYTES_TOTAL",
    "WARN_DAILY_USD", "HARD_CAP_USD", "MAX_QUEUE_DEPTH",
]
