"""Typed records for bp_writeback. §F8 convention: frozen+slots, PEP 604 unions."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

ProposalType = Literal["person", "project", "daily", "fact", "topic"]
QueueState = Literal["pending", "approved", "rejected", "expired"]


@dataclass(frozen=True, slots=True)
class WriteProposal:
    proposal_id: str
    type_: ProposalType
    title: str
    content: str
    confidence: float
    source_turn_id: str
    created_unix: float


@dataclass(frozen=True, slots=True)
class QueueRow:
    proposal_id: str
    proposal: WriteProposal
    state: QueueState
    approved_unix: float | None
    rejected_unix: float | None
