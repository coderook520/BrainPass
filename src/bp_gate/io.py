"""Disk-safe JSONL append (§G11).

Every module that writes a JSONL record uses safe_append_jsonl. Handles:
- disk pressure (statvfs pre-check, 100MB min free)
- O_NOFOLLOW (refuse symlinks)
- atomic append for lines < PIPE_BUF (4KB) via single os.write on O_APPEND fd
- rate-limited stderr warning on failure (1/minute per process)
- rotation when file exceeds size_cap_bytes

Callers get True on success, False on any skip. They must not raise.
"""
from __future__ import annotations
import json
import os
import pathlib
import threading
import time
from typing import Any

_LAST_WARN_AT: float = 0.0
_WARN_LOCK = threading.Lock()
_MIN_FREE_BYTES = 100 * 1024 * 1024
_DEFAULT_SIZE_CAP = 100 * 1024 * 1024


def _free_bytes(path: pathlib.Path) -> int:
    try:
        st = os.statvfs(str(path.parent))
        return st.f_bavail * st.f_frsize
    except OSError:
        return 0


def _warn(msg: str) -> None:
    global _LAST_WARN_AT
    now = time.time()
    with _WARN_LOCK:
        if now - _LAST_WARN_AT > 60:
            import sys
            print(f"[bp_gate.io] {msg}", file=sys.stderr)
            _LAST_WARN_AT = now


def _rotate_if_large(path: pathlib.Path, size_cap: int) -> None:
    try:
        if path.exists() and path.stat().st_size > size_cap:
            archive = path.with_suffix(path.suffix + ".1")
            if archive.exists():
                archive.unlink()
            path.rename(archive)
    except OSError:
        pass


def safe_append_jsonl(
    path: pathlib.Path | str,
    record: dict[str, Any],
    *,
    min_free_bytes: int = _MIN_FREE_BYTES,
    size_cap_bytes: int = _DEFAULT_SIZE_CAP,
) -> bool:
    path = pathlib.Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if _free_bytes(path) < min_free_bytes:
            return False
        _rotate_if_large(path, size_cap_bytes)
        line = (
            json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW
        fd = os.open(str(path), flags, 0o600)
        try:
            os.write(fd, line)
        finally:
            os.close(fd)
        return True
    except (OSError, UnicodeEncodeError, TypeError, ValueError) as e:
        _warn(f"append failed on {path.name}: {type(e).__name__}")
        return False
