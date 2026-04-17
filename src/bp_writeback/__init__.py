"""
bp_writeback — AI responses get parsed for save-worthy facts, proposals
queued for one-tap approval. Default mode: confirm.

Responsibility
--------------
After every /recall, inspect (user_message, ai_response) for facts worth
persisting. Dedupe against the existing vault. Enqueue proposals in a
SQLite queue. A separate CLI (bp-write review) walks the queue for the
user. Never auto-writes unless BP_WRITE_MODE=auto and confidence ≥ 0.85.

Moved off the /recall critical path (§G3): extractor runs async via the
bp_research executor AFTER the response is flushed to the client.

Public API
----------
- schedule_extract_async(user_message, ai_response) -> None
- handle_write_queue_list(handler_self, *, params) -> None
- handle_write_queue_approve(handler_self, *, params) -> None
- handle_write_queue_reject(handler_self, *, params) -> None
- register_endpoints(gated_post, gated_get) -> None

Storage
-------
- $XDG_STATE_HOME/brainpass/writeback-queue.sqlite (mode 0600)

Environment
-----------
- BP_WRITEBACK_ENABLED=true            master switch
- BP_WRITE_MODE=confirm                 confirm | auto | suggest | off
- BP_WRITE_CONFIDENCE_AUTO=0.85         threshold for auto mode
- BP_WRITE_QUEUE_TTL_DAYS=14
- BP_WRITE_QUEUE_MAX=500

Dependencies: stdlib only.

Failure modes
-------------
- Queue DB corrupted: CLI reports + suggests backup-and-recreate; librarian
  logs a warning but continues.
- Extractor LLM call fails: silently skipped (research executor catches).
- Vault permission flip: CLI prints hints + exits 2; row stays pending.

Gotchas
-------
- Extractor is fire-and-forget. A crash inside the worker doesn't surface
  to the user's /recall response.
- Proposals keyed by content-hash, so re-extracting the same turn is idempotent.
"""
from __future__ import annotations
import os

ENABLED = os.environ.get("BP_WRITEBACK_ENABLED", "true").lower() != "false"
WRITE_MODE = os.environ.get("BP_WRITE_MODE", "confirm").lower()
CONFIDENCE_AUTO = float(os.environ.get("BP_WRITE_CONFIDENCE_AUTO", "0.85"))
QUEUE_TTL_DAYS = int(os.environ.get("BP_WRITE_QUEUE_TTL_DAYS", "14"))
QUEUE_MAX = int(os.environ.get("BP_WRITE_QUEUE_MAX", "500"))

from .models import WriteProposal, QueueRow, ProposalType, QueueState
from .queue import WriteQueue, get_queue
from .extractor import extract_proposals, schedule_extract_async
from .proposer import dedupe_and_finalize
from .handlers import (
    handle_write_queue_list,
    handle_write_queue_approve,
    handle_write_queue_reject,
)


def register_endpoints(gated_post: set, gated_get: set) -> None:
    """Called by librarian.py on module load."""
    if not ENABLED:
        return
    # Gate set uses glob syntax (* matches one non-slash segment); {id}
    # is only for bp_routing named-capture. Using {id} in the gate set
    # would cause the glob matcher to treat them as literals — leaving
    # the endpoint ungated. (Caught by Police 5 cycle 1.)
    gated_get.add("/write-queue")
    gated_post.add("/write-queue/*/approve")
    gated_post.add("/write-queue/*/reject")
    # Router registration uses {id} for named capture (different vocab).
    try:
        from bp_routing import register_get, register_post
        register_get("/write-queue", handle_write_queue_list)
        register_post("/write-queue/{id}/approve", handle_write_queue_approve)
        register_post("/write-queue/{id}/reject", handle_write_queue_reject)
    except ImportError:
        pass


__all__ = [
    "WriteProposal", "QueueRow", "ProposalType", "QueueState",
    "WriteQueue", "get_queue",
    "extract_proposals", "schedule_extract_async",
    "dedupe_and_finalize",
    "handle_write_queue_list", "handle_write_queue_approve",
    "handle_write_queue_reject",
    "register_endpoints",
    "ENABLED", "WRITE_MODE", "CONFIDENCE_AUTO",
]
