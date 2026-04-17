"""Research trigger: smart fallback + inline/background split.

§F6/G3: 3s inline budget; timeout promotes to background.
§G9: all exceptions contained, shape-stable return.
§G12: topic dedup via _INFLIGHT lock.
§G13: bounded queue depth.
"""
from __future__ import annotations
import concurrent.futures
import hashlib
import re
import time
from datetime import datetime, timezone

from . import (
    _EXECUTOR, _INFLIGHT, _INFLIGHT_LOCK, ENABLED, MODE, THRESHOLD,
    INLINE_BUDGET_S, TIMEOUT_TOTAL, MAX_BYTES_PER_FETCH, MAX_BYTES_TOTAL,
    MAX_QUEUE_DEPTH, HARD_CAP_USD, module_ready,
)
from .fetcher import fetch_with_retry
from .sanitizer import sanitize
from .synthesizer import synthesize
from .cost_tracker import rolling_totals, record_cost, record_error
from .sources import plan_sources


def should_fire(vault_hits: int, explicit: bool | None = None) -> bool:
    if not module_ready():
        return False
    if explicit is not None:
        return explicit
    if MODE == "off":
        return False
    if MODE == "always":
        return True
    if MODE == "explicit":
        return False
    # smart (default)
    return vault_hits < THRESHOLD


def _query_to_topic(query: str) -> str:
    s = query.lower().strip()
    s = re.sub(r"[^a-z0-9\s]", "", s)
    words = [w for w in s.split() if len(w) >= 3][:5]
    return "-".join(words) if words else hashlib.sha256(query.encode()).hexdigest()[:12]


def run_inline_or_background(query: str, *, vault_hits: int) -> dict | None:
    """Caller is /recall. Returns:
      - None if research should not fire (or already backgrounded)
      - dict {'answer':..., 'citations':..., 'note_draft':..., 'cost_usd':..., 'background':False}
        if research completed inline
      - dict {'background': True, 'topic': ...} if promoted to background
    """
    if not should_fire(vault_hits):
        return None
    # Hard-cap check
    if HARD_CAP_USD is not None:
        totals = rolling_totals()
        if totals["24h_usd"] >= HARD_CAP_USD:
            return {"error": "hard_cap_exceeded", "skipped": True}
    topic = _query_to_topic(query)
    with _INFLIGHT_LOCK:
        existing = _INFLIGHT.get(topic)
        if existing is not None and not existing.done():
            future = existing
        else:
            if _EXECUTOR._work_queue.qsize() >= MAX_QUEUE_DEPTH:
                return {"error": "backpressured", "skipped": True}
            deadline = time.monotonic() + TIMEOUT_TOTAL
            future = _EXECUTOR.submit(_do_research_safe, query, deadline)
            _INFLIGHT[topic] = future
    try:
        result = future.result(timeout=INLINE_BUDGET_S)
        return result
    except concurrent.futures.TimeoutError:
        # background promoted; let it keep running under its 30s total deadline
        return {"background": True, "topic": topic}
    except Exception as e:
        record_error(hashlib.sha256(query.encode()).hexdigest()[:16],
                     type(e).__name__, str(e))
        return None


def _do_research_safe(query: str, deadline: float) -> dict:
    """Top-level catch-all. /recall NEVER raises from research."""
    try:
        return _do_research_impl(query, deadline)
    except Exception as e:
        return {
            "error": type(e).__name__,
            "fallback": True,
            "msg": str(e)[:500],
        }


def _do_research_impl(query: str, deadline: float) -> dict:
    from . import MAX_BYTES_PER_FETCH, MAX_BYTES_TOTAL
    sanitized: list[str] = []
    urls: list[str] = []
    total_bytes = 0
    for url in plan_sources(query):
        if time.monotonic() >= deadline:
            break
        if total_bytes >= MAX_BYTES_TOTAL:
            break
        try:
            body = fetch_with_retry(
                url, deadline=deadline, max_bytes=MAX_BYTES_PER_FETCH,
            )
        except (TimeoutError, ValueError, ConnectionError):
            continue
        except Exception:
            continue
        total_bytes += len(body)
        try:
            text = body.decode("utf-8", errors="replace")
        except Exception:
            continue
        from urllib.parse import urlparse
        domain = urlparse(url).hostname or "unknown"
        sanitized.append(sanitize(text, domain))
        urls.append(url)
    if not sanitized:
        return {"error": "no_sources", "fallback": True}
    if time.monotonic() >= deadline:
        return {"error": "deadline_exceeded", "fallback": True}
    result = synthesize(query, sanitized, urls)
    if result is None:
        return {"error": "synthesize_failed", "fallback": True}
    # Rough cost estimate — real cost set by librarian's LLM provider if it
    # exposes usage, else zero. Provider-aware implementation in a follow-up.
    result["citations"] = urls
    result["sources_fetched"] = len(urls)
    result["background"] = False
    _enqueue_writeback(result)
    return result


def _enqueue_writeback(result: dict) -> None:
    draft = result.get("note_draft") or {}
    if not draft:
        return
    title = str(draft.get("title", "")).strip()
    content = str(draft.get("content", "")).strip()
    if not title or not content:
        return
    try:
        from bp_writeback.queue import get_queue, make_proposal
    except ImportError:
        return
    try:
        proposal = make_proposal(
            type_="topic",
            title=title[:60],
            content=content,
            confidence=0.75,
            source_turn_id="auto-research",
        )
        get_queue().enqueue(proposal)
    except Exception:
        pass
