"""HTTP handlers for /changed and /timeline."""
from __future__ import annotations
import json
import time
from urllib.parse import parse_qs, urlparse

from .changed import walk_changed, _parse_iso
from .staleness import timeline


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


def handle_changed(h, *, params: dict[str, str]) -> None:
    q = _qs(h)
    since_str = q.get("since")
    if not since_str:
        since_unix = time.time() - 7 * 86400  # default: last 7 days
    else:
        parsed = _parse_iso(since_str)
        if parsed is None:
            _write_json(h, 400, {"error": "invalid `since` — expected ISO 8601"})
            return
        since_unix = parsed
    limit = int(q.get("limit", "200") or "200")
    files = walk_changed(since_unix, limit=limit)
    _write_json(h, 200, {"since_unix": since_unix, "files": files, "count": len(files)})


def handle_timeline(h, *, params: dict[str, str]) -> None:
    q = _qs(h)
    topic = q.get("topic", "").strip()
    if not topic:
        _write_json(h, 400, {"error": "missing `topic`"})
        return
    if len(topic) > 100:
        _write_json(h, 400, {"error": "topic too long"})
        return
    entries = timeline(topic)
    _write_json(h, 200, {
        "topic": topic,
        "timeline": entries,
        "count": len(entries),
        "conflicts_detected": [],  # LLM-based staleness deferred to v4 (§W14 in log)
    })
