"""HTTP handlers for /analytics/* endpoints."""
from __future__ import annotations
import json
from urllib.parse import parse_qs, urlparse

from .aggregator import hot_notes, dead_notes, query_patterns


def _write_json(h, code: int, body) -> None:
    payload = json.dumps(body).encode("utf-8")
    h.send_response(code)
    h.send_header("Content-Type", "application/json")
    h.send_header("Content-Length", str(len(payload)))
    h.end_headers()
    h.wfile.write(payload)


def _qs(h) -> dict[str, str]:
    u = urlparse(h.path)
    q = parse_qs(u.query)
    return {k: v[0] for k, v in q.items() if v}


def handle_hot_notes(h, *, params: dict[str, str]) -> None:
    q = _qs(h)
    days = int(q.get("days", "30") or "30")
    top = int(q.get("top", "20") or "20")
    results = hot_notes(days=days, top=top)
    _write_json(h, 200, {"days": days, "hot_notes": results, "count": len(results)})


def handle_dead_notes(h, *, params: dict[str, str]) -> None:
    q = _qs(h)
    days = int(q.get("days", "90") or "90")
    top = int(q.get("top", "50") or "50")
    results = dead_notes(days=days, top=top)
    _write_json(h, 200, {"days": days, "dead_notes": results, "count": len(results)})


def handle_query_patterns(h, *, params: dict[str, str]) -> None:
    q = _qs(h)
    days = int(q.get("days", "30") or "30")
    top = int(q.get("top", "20") or "20")
    results = query_patterns(days=days, top=top)
    _write_json(h, 200, {"days": days, "patterns": results, "count": len(results)})
