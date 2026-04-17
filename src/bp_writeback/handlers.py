"""HTTP handlers for /write-queue endpoints."""
from __future__ import annotations
import json
from typing import Any

from .queue import get_queue


def _write_json(h, code: int, body: dict[str, Any]) -> None:  # type-ok: JSON bodies are heterogeneous
    payload = json.dumps(body).encode("utf-8")
    h.send_response(code)
    h.send_header("Content-Type", "application/json")
    h.send_header("Content-Length", str(len(payload)))
    h.end_headers()
    h.wfile.write(payload)


def handle_write_queue_list(h, *, params: dict[str, str]) -> None:
    q = get_queue()
    rows = q.list_pending(limit=100)
    out = [{
        "proposal_id": r.proposal_id,
        "type": r.proposal.type_,
        "title": r.proposal.title,
        "content": r.proposal.content,
        "confidence": r.proposal.confidence,
        "created_unix": r.proposal.created_unix,
    } for r in rows]
    _write_json(h, 200, {"pending": out, "count": len(out)})


def handle_write_queue_approve(h, *, params: dict[str, str]) -> None:
    proposal_id = params.get("id", "")
    q = get_queue()
    row = q.get(proposal_id)
    if row is None:
        _write_json(h, 404, {"error": "proposal not found"})
        return
    if row.state != "pending":
        _write_json(h, 409, {"error": f"already {row.state}"})
        return
    try:
        from .extractor import _commit_to_vault
        _commit_to_vault(row.proposal)
    except (OSError, PermissionError) as e:
        _write_json(h, 500, {
            "error": "vault write failed",
            "detail": str(e)[:200],
            "hint": "check permissions on ~/BrainPass/vault",
        })
        return
    q.approve(proposal_id)
    _write_json(h, 200, {"approved": proposal_id, "title": row.proposal.title})


def handle_write_queue_reject(h, *, params: dict[str, str]) -> None:
    proposal_id = params.get("id", "")
    q = get_queue()
    ok = q.reject(proposal_id)
    if not ok:
        _write_json(h, 404, {"error": "proposal not pending or not found"})
        return
    _write_json(h, 200, {"rejected": proposal_id})
