"""Roll the recall-log into hot/dead/pattern reports. Streaming JSONL reader."""
from __future__ import annotations
import json
import os
import time
from collections import Counter
from typing import Iterator

try:
    from bp_gate.paths import bp_state_file
except ImportError:
    def bp_state_file(name):  # type: ignore
        import pathlib
        return pathlib.Path(os.path.expanduser(f"~/.local/state/brainpass/{name}"))


def _vault_path() -> str:
    return os.environ.get("VAULT_PATH") or os.path.expanduser("~/BrainPass/vault")


def _iter_log(min_ts: float | None = None) -> Iterator[dict]:
    path = bp_state_file("recall-log.jsonl")
    if not path.exists():
        return
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
                if min_ts is not None:
                    # ts is ISO — cheap compare as ISO strings (lexicographic works)
                    ts = rec.get("ts", "")
                    if not ts:
                        continue
                    try:
                        # Convert threshold to ISO for comparison (approx)
                        import datetime as _dt
                        thresh_dt = _dt.datetime.fromtimestamp(min_ts, tz=_dt.timezone.utc)
                        if ts < thresh_dt.isoformat().replace("+00:00", "Z"):
                            continue
                    except Exception:
                        pass
                yield rec
    except OSError:
        return


def hot_notes(days: int = 30, top: int = 20) -> list[dict]:
    min_ts = time.time() - days * 86400
    counter: Counter[str] = Counter()
    for rec in _iter_log(min_ts):
        for p in rec.get("surfaced", []):
            counter[p] += 1
    return [{"path": p, "recall_count": c} for p, c in counter.most_common(top)]


def dead_notes(days: int = 90, top: int = 50) -> list[str]:
    min_ts = time.time() - days * 86400
    seen: set[str] = set()
    for rec in _iter_log(min_ts):
        for p in rec.get("surfaced", []):
            seen.add(p)
    vault = _vault_path()
    if not os.path.isdir(vault):
        return []
    all_notes: list[str] = []
    for root, dirs, files in os.walk(vault, followlinks=False):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.endswith(".md"):
                rel = os.path.relpath(os.path.join(root, f), vault)
                all_notes.append(rel)
    dead = [p for p in all_notes if p not in seen]
    dead.sort()
    return dead[:top]


def query_patterns(days: int = 30, top: int = 20) -> list[dict]:
    min_ts = time.time() - days * 86400
    word_counter: Counter[str] = Counter()
    total = 0
    for rec in _iter_log(min_ts):
        q = rec.get("query_scrubbed", "").lower()
        total += 1
        for w in q.split():
            w = "".join(c for c in w if c.isalnum())
            if len(w) >= 4:
                word_counter[w] += 1
    return [
        {"topic_word": w, "occurrences": c, "fraction_of_queries": c / max(1, total)}
        for w, c in word_counter.most_common(top)
    ]
