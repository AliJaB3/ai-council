"""Dashboard API data contracts."""
from dataclasses import dataclass

@dataclass
class StreamEvent:
    event_id: str
    run_id: str
    seq: int
    timestamp: float
    event_type: str
    payload: dict

@dataclass
class RunSnapshot:
    run_id: str
    topic: str
    status: str
    confidence_score: float
    duration_s: float
    created_at: str
    verdict: dict
    opinions: list[dict]
    graph: dict
    seat_weights: dict
    experiment_spec: dict | None

@dataclass
class SeatTelemetry:
    role: str
    title: str
    avatar: str
    model: str
    latency_ms: float
    brier_score: float | None
    weight: float
    status: str
