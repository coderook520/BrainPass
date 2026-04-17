"""Credential scrubber — literal regex replacement, no shell, no interpolation.

Removes Groq/XAI/OpenAI-style API keys and bearer tokens from strings
before they hit logs, error messages, or audit output.
"""
import re

_PATTERNS = [
    # Order matters — more specific prefixes first.
    (re.compile(rb"sk-ant-[A-Za-z0-9_\-]{20,}"), b"sk-ant-REDACTED"),
    (re.compile(rb"gsk_[A-Za-z0-9_\-]{20,}"), b"gsk_REDACTED"),
    (re.compile(rb"xai-[A-Za-z0-9_\-]{20,}"), b"xai-REDACTED"),
    (re.compile(rb"sk-[A-Za-z0-9_\-]{20,}"), b"sk-REDACTED"),
    (re.compile(rb"Bearer\s+[A-Za-z0-9_\-\.]{20,}"), b"Bearer REDACTED"),
]


def scrub(data: bytes) -> bytes:
    for pat, repl in _PATTERNS:
        data = pat.sub(repl, data)
    return data


def scrub_str(s) -> str:
    if not isinstance(s, str):
        s = str(s)
    return scrub(s.encode("utf-8", "replace")).decode("utf-8", "replace")
