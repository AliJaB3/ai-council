"""Apex data contracts."""
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Claim:
    claim_id: str
    author_role: str
    proposition: str
    confidence: float = 0.5
    evidence_refs: list[str] = field(default_factory=list)

@dataclass(frozen=True)
class EvidenceEnvelope:
    evidence_id: str
    source_uri: str
    content: str
    is_trusted: bool = False
    version: int = 1
    timestamp: float = 0.0

@dataclass
class SearchNode:
    node_id: str
    parent_id: str | None = None
    action: str = ''
    state_snapshot: dict = field(default_factory=dict)
    visits: int = 0
    value_sum: float = 0.0
    falsification_penalty: float = 0.0

@dataclass(frozen=True)
class ObjectionRecord:
    objection_id: str
    target_claim_id: str
    counter_code: str = ''
    status: str = 'PENDING'

@dataclass(frozen=True)
class Ballot:
    voter_id: str
    proposal_id: str
    votes: float = 0.0
    cost: float = 0.0
