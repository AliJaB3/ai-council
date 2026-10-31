"""Data structures for the ideation and crucible workshops."""
from dataclasses import dataclass, field
from enum import Enum


class Domain(str, Enum):
    BINANCE_ALGO = 'BINANCE_ALGO'
    SOLANA_INFRA = 'SOLANA_INFRA'
    LOW_LATENCY_DISTRIBUTED = 'LOW_LATENCY_DISTRIBUTED'
    OFFENSIVE_SEC = 'OFFENSIVE_SEC'
    AI_MODELS = 'AI_MODELS'
    GENERAL = 'GENERAL'


class IdeaStatus(str, Enum):
    PROPOSED = 'PROPOSED'
    TIER_0_REJECTED = 'TIER_0_REJECTED'
    TIER_1_REJECTED = 'TIER_1_REJECTED'
    TIER_2_FALSIFIED = 'TIER_2_FALSIFIED'
    FALSIFIED = 'FALSIFIED'  # Legacy workshop
    VALIDATED = 'VALIDATED'
    PROTOTYPED = 'PROTOTYPED'


class VerificationLevel(str, Enum):
    HYPOTHESIS = 'HYPOTHESIS'
    SIMULATED = 'SIMULATED'
    HISTORICAL_REPLAY = 'HISTORICAL_REPLAY'
    EMPIRICALLY_PROVEN = 'EMPIRICALLY_PROVEN'


@dataclass
class InvariantContract:
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)
    complexity_time: str = 'O(1)'
    complexity_space: str = 'O(1)'
    max_latency_budget_ns: int = 100_000
    max_capital_risk_usd: float = 0.0


@dataclass
class CausalMechanism:
    trigger_event: str
    causal_node: str
    intervention: str
    predicted_outcome: str
    falsification_metric: str
    falsification_threshold: float


@dataclass
class Anomaly:
    id: str
    source: str
    metric: str
    z_score: float
    details: dict
    created_at: str


@dataclass
class IdeaCard:
    id: str
    title: str
    domain: Domain
    problem_statement: str
    causal_mechanism: CausalMechanism
    baseline_reference: str
    cheapest_falsification_test: str
    secondary_domains: list[Domain] = field(default_factory=list)
    invariant_contract: InvariantContract = field(default_factory=InvariantContract)
    status: IdeaStatus = IdeaStatus.PROPOSED
    verification_level: VerificationLevel = VerificationLevel.HYPOTHESIS
    falsification_reason: str = ''
    iteration_depth: int = 0
    created_at: str = ''
    token_budget: int = 5000
    metrics: dict = field(default_factory=dict)
