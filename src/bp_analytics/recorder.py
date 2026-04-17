"""JSONL recall-log writer. Privacy-scrubbed, disk-safe (§G11), ReDoS-safe (§G8)."""
from __future__ import annotations
import hashlib
import os
import re
import time
from datetime import datetime, timezone

try:
    from bp_gate.scrub_keys import scrub_str
    from bp_gate.io import safe_append_jsonl
    from bp_gate.paths import bp_state_file
    _BP_GATE_AVAILABLE = True
except ImportError:
    _BP_GATE_AVAILABLE = False
    def scrub_str(s):  # type: ignore
        return s
    def safe_append_jsonl(path, rec, **kwargs):  # type: ignore
        try:
            import json
            os.makedirs(os.path.dirname(str(path)), exist_ok=True)
            with open(str(path), "a") as f:
                f.write(json.dumps(rec) + "\n")
            return True
        except OSError:
            return False
    def bp_state_file(name):  # type: ignore
        import pathlib
        return pathlib.Path(os.path.expanduser(f"~/.local/state/brainpass/{name}"))


# §G8 — ReDoS defense. Python's `re` module does not release the GIL during
# matching, so thread-based runtime timeouts are not reliable for regex.
# Our v3 strategy is STRUCTURAL PRE-FILTER only:
#   1. _REDOS_SIGS rejects patterns whose shape is known to trigger
#      catastrophic backtracking (nested unbounded quantifiers, etc.)
#   2. _benchmark_pattern runs each pattern against a SMALL probe set
#      (max 50 chars) — safe patterns complete in microseconds; patterns
#      that would hang on small inputs are structurally already caught by
#      _REDOS_SIGS.
#
# Documented limitation: a maliciously-crafted pattern that bypasses both
# the structural sigs AND runs fast on 50-char probes but slow on
# real queries is possible in theory. The mitigation is documentation:
# BP_PII_SCRUB_FILE is trusted-user input, not attacker input.
#
# Future: swap to the `regex` 3rd-party package (supports TIMEOUT) in a
# follow-up PR if the structural filter proves inadequate.
_REDOS_PROBES = ["a" * 50, "ab" * 25, "a" * 25 + "!", ""]
_REDOS_SIGS = [
    re.compile(r"\([^)]*\*\)[*+]"),
    re.compile(r"\([^)]*\+\)[*+]"),
    re.compile(r"\([^|)]*\|[^)]*\)\+"),
    re.compile(r"\(\?:.*\*\)[*+]"),
]


def _is_redos_signature(pattern: str) -> bool:
    return any(sig.search(pattern) for sig in _REDOS_SIGS)


def _benchmark_pattern(pat: re.Pattern, budget_s: float = 0.05) -> bool:
    """Benchmark pattern against small probes. Only useful as a smoke check
    after structural pre-filter — does NOT protect against adversarial
    patterns that pass the structural filter. See module docstring.
    """
    for probe in _REDOS_PROBES:
        t0 = time.monotonic()
        try:
            pat.search(probe)
        except Exception:
            return False
        if time.monotonic() - t0 > budget_s:
            return False
    return True


def _load_user_pii_patterns() -> list[re.Pattern]:
    path = os.environ.get("BP_PII_SCRUB_FILE")
    if not path or not os.path.isfile(path):
        return []
    try:
        st = os.stat(path)
    except OSError:
        return []
    if st.st_uid != os.geteuid():
        return []
    if st.st_mode & 0o077:
        return []
    patterns: list[re.Pattern] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if _is_redos_signature(line):
                    continue
                try:
                    p = re.compile(line)
                except re.error:
                    continue
                if not _benchmark_pattern(p):
                    continue
                patterns.append(p)
    except OSError:
        return []
    return patterns


_PII_PATTERNS: list[re.Pattern] = _load_user_pii_patterns()


def scrub_query(q: str) -> str:
    q = scrub_str(q)
    for pat in _PII_PATTERNS:
        q = pat.sub("[REDACTED]", q)
    return q


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def record_recall(
    query: str,
    surfaced: list[str],
    duration_ms: int,
    vault_hits: int,
    research_fired: bool,
) -> bool:
    """Record one /recall event. Returns True on success, False on skip."""
    from . import ENABLED
    if not ENABLED:
        return False
    q_scrubbed = scrub_query(query)[:500]
    q_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]
    rec = {
        "ts": _now_iso(),
        "query_hash": q_hash,
        "query_scrubbed": q_scrubbed,
        "surfaced": surfaced[:20],
        "duration_ms": int(duration_ms),
        "vault_hits": int(vault_hits),
        "research_fired": bool(research_fired),
    }
    return safe_append_jsonl(bp_state_file("recall-log.jsonl"), rec)
