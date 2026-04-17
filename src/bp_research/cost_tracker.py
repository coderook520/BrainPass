"""Append-only per-call cost log + rolling summaries."""
from __future__ import annotations
import json
import time
from datetime import datetime, timezone

try:
    from bp_gate.paths import bp_state_file
    from bp_gate.io import safe_append_jsonl
except ImportError:
    import os
    def bp_state_file(name):  # type: ignore
        import pathlib
        return pathlib.Path(os.path.expanduser(f"~/.local/state/brainpass/{name}"))
    def safe_append_jsonl(path, rec, **kwargs):  # type: ignore
        try:
            os.makedirs(os.path.dirname(str(path)), exist_ok=True)
            with open(str(path), "a") as f:
                f.write(json.dumps(rec) + "\n")
            return True
        except OSError:
            return False


def record_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
) -> None:
    rec = {
        "ts": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "provider": provider,
        "model": model,
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "cost_usd": round(float(cost_usd), 6),
    }
    safe_append_jsonl(bp_state_file("research-cost.jsonl"), rec)


def rolling_totals() -> dict[str, float]:
    """Returns {'24h_usd': X, '7d_usd': Y}. Cheap — streams JSONL."""
    now = time.time()
    total_24h = 0.0
    total_7d = 0.0
    path = bp_state_file("research-cost.jsonl")
    if not path.exists():
        return {"24h_usd": 0.0, "7d_usd": 0.0}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                ts = rec.get("ts")
                if not ts:
                    continue
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    age = now - dt.timestamp()
                except ValueError:
                    continue
                cost = float(rec.get("cost_usd", 0.0))
                if age < 86400:
                    total_24h += cost
                if age < 7 * 86400:
                    total_7d += cost
    except OSError:
        pass
    return {"24h_usd": round(total_24h, 4), "7d_usd": round(total_7d, 4)}


def record_error(query_hash: str, error_type: str, msg: str) -> None:
    rec = {
        "ts": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "query_hash": query_hash,
        "error": error_type,
        "msg": msg[:500],
    }
    safe_append_jsonl(bp_state_file("research-error.jsonl"), rec)
