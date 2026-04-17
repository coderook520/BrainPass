"""SQLite-backed write-back queue.

Schema: one row per proposal. States transition pending → approved | rejected | expired.
Concurrency: check_same_thread=False + module-level lock on writes (WAL handles reads).
"""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3
import threading
import time
from typing import Iterator

from .models import WriteProposal, QueueRow, QueueState

try:
    from bp_gate.paths import bp_state_file
except ImportError:
    bp_state_file = None  # type: ignore

_SCHEMA = """
CREATE TABLE IF NOT EXISTS proposals (
    proposal_id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence REAL NOT NULL,
    source_turn_id TEXT NOT NULL,
    created_unix REAL NOT NULL,
    state TEXT NOT NULL DEFAULT 'pending',
    approved_unix REAL,
    rejected_unix REAL
);
CREATE INDEX IF NOT EXISTS proposals_state_idx ON proposals(state);
CREATE INDEX IF NOT EXISTS proposals_created_idx ON proposals(created_unix);
"""

_LOCK = threading.Lock()


def _default_db_path() -> str:
    if bp_state_file is not None:
        return str(bp_state_file("writeback-queue.sqlite"))
    return os.path.expanduser("~/.local/state/brainpass/writeback-queue.sqlite")


def _proposal_id(title: str, content: str, source_turn_id: str) -> str:
    h = hashlib.sha256()
    h.update(title.encode("utf-8"))
    h.update(b"\0")
    h.update(content.encode("utf-8"))
    h.update(b"\0")
    h.update(source_turn_id.encode("utf-8"))
    return h.hexdigest()[:16]


class WriteQueue:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or _default_db_path()
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            isolation_level=None,  # autocommit
        )
        try:
            os.chmod(self.db_path, 0o600)
        except OSError:
            pass
        with _LOCK:
            self._conn.executescript("PRAGMA journal_mode=WAL; " + _SCHEMA)

    def enqueue(self, proposal: WriteProposal) -> bool:
        """Insert proposal. Returns False if already present (idempotent)."""
        with _LOCK:
            try:
                self._conn.execute(
                    "INSERT INTO proposals(proposal_id,type,title,content,confidence,"
                    "source_turn_id,created_unix,state) VALUES (?,?,?,?,?,?,?,?)",
                    (proposal.proposal_id, proposal.type_, proposal.title, proposal.content,
                     proposal.confidence, proposal.source_turn_id, proposal.created_unix,
                     "pending"),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def list_pending(self, limit: int = 50) -> list[QueueRow]:
        cur = self._conn.execute(
            "SELECT proposal_id,type,title,content,confidence,source_turn_id,"
            "created_unix,state,approved_unix,rejected_unix "
            "FROM proposals WHERE state='pending' "
            "ORDER BY created_unix DESC LIMIT ?", (limit,))
        rows = []
        for r in cur.fetchall():
            prop = WriteProposal(
                proposal_id=r[0], type_=r[1], title=r[2], content=r[3],  # type: ignore
                confidence=r[4], source_turn_id=r[5], created_unix=r[6],
            )
            rows.append(QueueRow(
                proposal_id=r[0], proposal=prop, state=r[7],  # type: ignore
                approved_unix=r[8], rejected_unix=r[9],
            ))
        return rows

    def get(self, proposal_id: str) -> QueueRow | None:
        cur = self._conn.execute(
            "SELECT proposal_id,type,title,content,confidence,source_turn_id,"
            "created_unix,state,approved_unix,rejected_unix "
            "FROM proposals WHERE proposal_id=?", (proposal_id,))
        r = cur.fetchone()
        if r is None:
            return None
        prop = WriteProposal(
            proposal_id=r[0], type_=r[1], title=r[2], content=r[3],  # type: ignore
            confidence=r[4], source_turn_id=r[5], created_unix=r[6],
        )
        return QueueRow(
            proposal_id=r[0], proposal=prop, state=r[7],  # type: ignore
            approved_unix=r[8], rejected_unix=r[9],
        )

    def approve(self, proposal_id: str) -> bool:
        with _LOCK:
            cur = self._conn.execute(
                "UPDATE proposals SET state='approved', approved_unix=? "
                "WHERE proposal_id=? AND state='pending'",
                (time.time(), proposal_id),
            )
            return cur.rowcount > 0

    def reject(self, proposal_id: str) -> bool:
        with _LOCK:
            cur = self._conn.execute(
                "UPDATE proposals SET state='rejected', rejected_unix=? "
                "WHERE proposal_id=? AND state='pending'",
                (time.time(), proposal_id),
            )
            return cur.rowcount > 0

    def expire_stale(self, max_age_seconds: float) -> int:
        cutoff = time.time() - max_age_seconds
        with _LOCK:
            cur = self._conn.execute(
                "UPDATE proposals SET state='expired' "
                "WHERE state='pending' AND created_unix < ?", (cutoff,))
            return cur.rowcount

    def count(self, state: QueueState | None = None) -> int:
        if state is None:
            cur = self._conn.execute("SELECT COUNT(*) FROM proposals")
        else:
            cur = self._conn.execute("SELECT COUNT(*) FROM proposals WHERE state=?", (state,))
        return int(cur.fetchone()[0])

    def close(self) -> None:
        with _LOCK:
            self._conn.close()


_SINGLETON: WriteQueue | None = None


def get_queue() -> WriteQueue:
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = WriteQueue()
    return _SINGLETON


def make_proposal(
    *,
    type_: str,
    title: str,
    content: str,
    confidence: float,
    source_turn_id: str,
) -> WriteProposal:
    return WriteProposal(
        proposal_id=_proposal_id(title, content, source_turn_id),
        type_=type_,  # type: ignore
        title=title,
        content=content,
        confidence=confidence,
        source_turn_id=source_turn_id,
        created_unix=time.time(),
    )


def init_db(path: str) -> None:
    """Called by install.sh via `python3 -m bp_writeback.queue --init <path>`."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)
    conn.executescript("PRAGMA journal_mode=WAL; " + _SCHEMA)
    conn.close()
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "--init":
        init_db(sys.argv[2])
        print(f"initialized {sys.argv[2]}")
