"""/changed?since=<iso> — recent-file walker over the vault."""
from __future__ import annotations
import os
import time
from datetime import datetime, timezone


def _vault_path() -> str:
    return os.environ.get("VAULT_PATH") or os.path.expanduser("~/BrainPass/vault")


def _parse_iso(iso: str) -> float | None:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (ValueError, TypeError):
        return None


def walk_changed(since_unix: float, limit: int = 200) -> list[dict]:
    vault = _vault_path()
    out: list[dict] = []
    if not os.path.isdir(vault):
        return []
    for root, dirs, files in os.walk(vault, followlinks=False):
        # Skip hidden + .dreams (sandboxed)
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if not f.endswith(".md"):
                continue
            full = os.path.join(root, f)
            try:
                st = os.stat(full)
            except OSError:
                continue
            if st.st_mtime < since_unix:
                continue
            rel = os.path.relpath(full, vault)
            summary = _file_summary(full)
            out.append({
                "path": rel,
                "mtime_unix": st.st_mtime,
                "mtime_iso": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                "summary": summary,
            })
            if len(out) >= limit:
                break
        if len(out) >= limit:
            break
    out.sort(key=lambda r: r["mtime_unix"], reverse=True)
    return out


def _file_summary(path: str, cap: int = 200) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            body = f.read(cap + 50)
    except OSError:
        return ""
    body = body.strip()
    if len(body) > cap:
        body = body[:cap].rstrip() + "..."
    return body
