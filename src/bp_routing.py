"""bp_routing — pure-function endpoint router for the librarian.

Responsibility
--------------
Given (method, path), find and dispatch a matching handler. Zero state
beyond the route table, which is built at module-import time and read-only
afterward.

Public API
----------
- normalize_request_path(raw) -> str | None    : canonicalize or signal 400
- register_get(pattern, handler) -> None
- register_post(pattern, handler) -> None
- dispatch(method, path, handler_self) -> bool : returns True if a handler ran

Pattern syntax: exact + glob + named captures.
  '*'       -> [^/]+        (one-or-more non-slash)
  '?'       -> [^/]          (exactly one non-slash)
  '{name}'  -> ([^/]+)      (one captured segment, bound to `name`)

Design notes (cross-references to the approved plan):
- §G1 — _path_in_gated_set and dispatch share the same pattern vocab
- §F2 / §G6 — normalize_request_path is the ONE canonicalizer; gate, router,
  and fall-through all call it. Any difference between raw and normalized
  input is 400 — that closes parser-differential bypass.
- §G2 — single-threaded HTTPServer; routes appended only at import time,
  no locks needed at request time.
- §F10 / §G16 — dispatch contract: handler returns None; exceptions caught
  upstream by the caller (librarian's do_POST/do_GET wrapper).

Storage: none.

Dependencies: stdlib only.

Gotchas:
- Register handlers in each feature module's __init__.py at import time.
- Never call register_* from a request handler — it would be a data race
  under any future threaded-server migration.
"""
from __future__ import annotations
import posixpath
import re
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import unquote


def normalize_request_path(raw: str) -> str | None:
    """Return canonical path (always starts with '/') or None to force 400.

    Any discrepancy between decoded input and posixpath.normpath result is
    refused — this closes slash, dot, backtrack, and empty-segment ambiguity
    without needing a second parser.
    """
    if not raw:
        return None
    for sep in ("#", "?", ";"):
        if sep in raw:
            raw = raw.split(sep, 1)[0]
    try:
        decoded = unquote(raw, errors="strict")
    except (UnicodeDecodeError, UnicodeError):
        return None
    # Any decoding = rejection. `/recall%20` decodes to `/recall ` which is
    # not a canonical path, and the gate must refuse encoded inputs to
    # prevent parser differential.
    if decoded != raw:
        return None
    if "%" in decoded:
        return None
    # Reject double-slash at start (posixpath.normpath preserves POSIX `//`)
    if decoded.startswith("//"):
        return None
    normalized = posixpath.normpath(decoded)
    if not normalized.startswith("/"):
        return None
    if normalized != decoded:
        return None
    return normalized


def _compile_pattern(pattern: str) -> tuple[re.Pattern, tuple[str, ...]]:
    parts: list[str] = []
    names: list[str] = []
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "{":
            end = pattern.index("}", i)
            names.append(pattern[i + 1:end])
            parts.append(r"([^/]+)")
            i = end + 1
        elif ch == "*":
            parts.append(r"[^/]+")
            i += 1
        elif ch == "?":
            parts.append(r"[^/]")
            i += 1
        else:
            parts.append(re.escape(ch))
            i += 1
    return re.compile("^" + "".join(parts) + "$"), tuple(names)


@dataclass(frozen=True, slots=True)
class Route:
    pattern: str
    handler: Callable
    regex: re.Pattern = field(init=False)
    param_names: tuple[str, ...] = field(init=False, default=())

    def __post_init__(self) -> None:
        regex, names = _compile_pattern(self.pattern)
        object.__setattr__(self, "regex", regex)
        object.__setattr__(self, "param_names", names)


_GET_ROUTES: list[Route] = []
_POST_ROUTES: list[Route] = []


def register_get(pattern: str, handler: Callable) -> None:
    _GET_ROUTES.append(Route(pattern, handler))


def register_post(pattern: str, handler: Callable) -> None:
    _POST_ROUTES.append(Route(pattern, handler))


def dispatch(method: str, path: str, handler_self) -> bool:
    """Return True if a handler ran. False if no route matched."""
    routes = _GET_ROUTES if method == "GET" else _POST_ROUTES if method == "POST" else []
    for r in routes:
        m = r.regex.match(path)
        if m:
            params: dict[str, str] = dict(zip(r.param_names, m.groups()))
            r.handler(handler_self, params=params)
            return True
    return False


def _reset_routes_for_tests() -> None:
    """Test-only helper — module-level mutation outside import time."""
    _GET_ROUTES.clear()
    _POST_ROUTES.clear()
