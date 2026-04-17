"""Canonical state-dir helper (§G5).

Every BrainPass module that needs persistent state uses this. Prevents path
drift (see Phase-2 P3-5: gate_mixin was hardcoding ~/.local/state/brainpass
while new modules used $XDG_STATE_HOME).
"""
from __future__ import annotations
import os
import pathlib


def bp_state_dir() -> pathlib.Path:
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "state"
    )
    d = pathlib.Path(base) / "brainpass"
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except OSError:
        pass
    return d


def bp_state_file(name: str) -> pathlib.Path:
    return bp_state_dir() / name
