"""Stable records exchanged by the council, SEAL, and memory providers."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import uuid

class TrustState(str, Enum):
    QUARANTINED = 'QUARANTINED'
    VALIDATED = 'VALIDATED'
    REVOKED = 'REVOKED'
    EXPIRED = 'EXPIRED'

class Verdict(str, Enum):
    PROMOTABLE = 'PROMOTABLE'
    REJECTED = 'REJECTED'
    HARD_FAIL = 'HARD_FAIL'

def content_digest(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()

@dataclass
class MemoryRecord:
    payload: object
    tenant_id: str
    session_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: int = 1
    content_hash: str = ''
    provenance: object = field(default_factory=dict)
    evidence_refs: list = field(default_factory=list)
    drift_score: float = 0.0
    trust_state: str = TrustState.QUARANTINED
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str | None = None
    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = content_digest(self.payload)

@dataclass
class ExperimentResult:
    candidate_hash: str
    base_revision: str
    sandbox_profile: str
    metrics: dict
    verdict: str
