"""Cross-time staleness detection for a given topic slug."""
from __future__ import annotations
import os
import re
from datetime import datetime, timezone


def _vault_path() -> str:
    return os.environ.get("VAULT_PATH") or os.path.expanduser("~/BrainPass/vault")


def timeline(topic: str, max_entries: int = 20) -> list[dict]:
    """Return chronological entries that mention the topic, each with a
    one-line summary.

    This is a cheap scan — it does NOT call an LLM. Staleness detection
    (contradiction flagging) is a separate LLM call invoked by the handler
    when BP_TEMPORAL_STALENESS=true.
    """
    vault = _vault_path()
    if not os.path.isdir(vault):
        return []
    topic_rx = re.compile(re.escape(topic), re.IGNORECASE)
    hits: list[dict] = []
    for root, dirs, files in os.walk(vault, followlinks=False):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if not f.endswith(".md"):
                continue
            full = os.path.join(root, f)
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as fh:
                    body = fh.read(50000)
            except OSError:
                continue
            if not topic_rx.search(body):
                continue
            try:
                st = os.stat(full)
            except OSError:
                continue
            # First line containing the topic
            claim = _extract_claim(body, topic_rx)
            hits.append({
                "date_iso": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                "mtime_unix": st.st_mtime,
                "source_path": os.path.relpath(full, vault),
                "claim": claim,
            })
    hits.sort(key=lambda h: h["mtime_unix"])
    return hits[:max_entries]


def _extract_claim(body: str, topic_rx: re.Pattern) -> str:
    for line in body.splitlines():
        if topic_rx.search(line):
            stripped = line.strip().lstrip("-*# ").strip()
            if len(stripped) > 200:
                stripped = stripped[:200] + "..."
            return stripped
    return ""
