"""Data structures for an ideation workshop."""
from dataclasses import dataclass, field
from enum import Enum

from ..skills.models import Domain


@dataclass
class Anomaly:
    id: str
    source: str
    metric: str
    z_score: float
    details: dict
    created_at: str


class IdeaStatus(str, Enum):
    PROPOSED = 'PROPOSED'
    FALSIFIED = 'FALSIFIED'
    VALIDATED = 'VALIDATED'
    PROTOTYPED = 'PROTOTYPED'


@dataclass
class IdeaCard:
    id: str
    title: str
    domain: Domain
    problem_statement: str
    causal_mechanism: str
    baseline_reference: str
    cheapest_falsification_test: str
    token_budget: int = 5000
    status: IdeaStatus = IdeaStatus.PROPOSED
    falsification_reason: str = ''
    metrics: dict = field(default_factory=dict)
    created_at: str = ''
