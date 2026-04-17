"""Exponential decay scoring — recent notes outrank old notes."""
from __future__ import annotations
import time


def decay_score(mtime_unix: float, now_unix: float | None = None,
                 half_life_days: float = 30.0) -> float:
    """Returns 1.0 at age=0, 0.5 at age=half_life, 0.25 at 2x, etc."""
    if now_unix is None:
        now_unix = time.time()
    age_days = max(0.0, (now_unix - mtime_unix) / 86400.0)
    if half_life_days <= 0:
        return 1.0
    return 2.0 ** (-age_days / half_life_days)


def apply_decay(
    ranked: list[tuple[str, float]],
    *,
    mtime_lookup,
    half_life_days: float = 30.0,
    now_unix: float | None = None,
) -> list[tuple[str, float]]:
    """Re-rank (path, rrf_score) list by multiplying in decay.

    mtime_lookup is a callable path -> float (mtime unix). Paths that the
    lookup cannot resolve keep their original rank with decay 1.0.
    """
    if now_unix is None:
        now_unix = time.time()
    out: list[tuple[str, float]] = []
    for path, score in ranked:
        try:
            m = float(mtime_lookup(path))
        except Exception:
            m = now_unix
        out.append((path, score * decay_score(m, now_unix, half_life_days)))
    out.sort(key=lambda r: r[1], reverse=True)
    return out
