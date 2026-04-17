"""Dedupe proposals against existing vault notes.

Conservative: if a file with the same slug exists, shift to append-mode
(the CLI will show the existing content + the new content, user decides).
"""
from __future__ import annotations
import os
from dataclasses import replace

from .models import WriteProposal


def _vault_path() -> str:
    return os.environ.get("VAULT_PATH") or os.path.expanduser("~/BrainPass/vault")


def dedupe_and_finalize(proposals: list[WriteProposal]) -> list[WriteProposal]:
    """Adjust each proposal's title if a vault file already exists.

    We don't auto-merge — we let the CLI show both and let the user decide.
    What we DO is disambiguate the slug (slug.md -> slug-v2.md) so enqueue()
    doesn't silently overwrite a previously-approved file.
    """
    vault = _vault_path()
    out: list[WriteProposal] = []
    for p in proposals:
        subdir = {
            "person": "people", "project": "projects", "daily": "daily",
            "fact": "topics", "topic": "topics",
        }.get(p.type_, "topics")
        path = os.path.join(vault, subdir, f"{p.title}.md")
        if not os.path.exists(path):
            out.append(p)
            continue
        # Disambiguate
        n = 2
        while os.path.exists(os.path.join(vault, subdir, f"{p.title}-v{n}.md")):
            n += 1
            if n > 20:
                break
        new_title = f"{p.title}-v{n}"
        out.append(replace(p, title=new_title))
    return out
