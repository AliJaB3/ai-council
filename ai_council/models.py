"""Serializable council records."""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

class Stance(str, Enum):
    SUPPORT = "SUPPORT"
    OPPOSE = "OPPOSE"
    AMEND = "AMEND"

def _confidence(value: Any) -> int:
    value = int(value)
    if not 1 <= value <= 10:
        raise ValueError("confidence must be between 1 and 10")
    return value

@dataclass
class Claim:
    text: str
    source: str = ""
    confidence: int = 5
    dependencies: list[str] = field(default_factory=list)
    invalidation_conditions: list[str] = field(default_factory=list)
    def __post_init__(self):
        self.confidence = _confidence(self.confidence)

@dataclass
class SeatOpinion:
    role: str
    title: str = ""
    avatar: str = ""
    model_family: str = ""
    model_used: str = ""
    latency_ms: float = 0
    stance: Stance = Stance.AMEND
    confidence: int = 5
    argument: str = ""
    novel_insight: str = ""
    key_risk: str = ""
    condition: str = ""
    claims: list[Claim] = field(default_factory=list)
    correlation_id: str = ""
    def __post_init__(self):
        self.stance = Stance(self.stance.upper())
        self.confidence = _confidence(self.confidence)
        self.claims = [c if isinstance(c, Claim) else Claim(**c) for c in self.claims]

@dataclass
class DialecticTurn:
    seat_role: str
    challenge_target: str = ""
    challenge_point: str = ""
    synergy_target: str = ""
    synergy_point: str = ""
    evolved_stance: Stance = Stance.AMEND
    text: str = ""
    def __post_init__(self):
        self.evolved_stance = Stance(self.evolved_stance.upper())

@dataclass
class CouncilVerdict:
    id: str = field(default_factory=lambda: str(uuid4()))
    topic: str = ""
    status: str = "COMPLETE"
    confidence_score: float = 0.0
    executive_verdict: str = ""
    emergent_architecture: str = ""
    consensus_analysis: str = ""
    implementation_blueprint: str = ""
    risk_matrix: str = ""
    kill_switch_criteria: str = ""
    judge_model: str = ""
    duration_s: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    audit_report: dict = field(default_factory=dict)
    early_exit: bool = False
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    experiment_spec: dict | None = None
    def to_dict(self):
        return asdict(self)
