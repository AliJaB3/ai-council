"""Claim relationships and an interpretable stance agreement score."""
import re
from itertools import combinations
from collections import Counter
from dataclasses import asdict, dataclass, field
from uuid import uuid4

_NEGATION = re.compile(r"\b(?:not|never|no|cannot|can't|won't|doesn't|isn't|shouldn't)\b", re.I)
def _signature(text):
    text = text.lower().replace("can't", "can not").replace("won't", "will not").replace("doesn't", "does not").replace("isn't", "is not").replace("shouldn't", "should not")
    negative = bool(_NEGATION.search(text))
    words = re.findall(r"\w+", _NEGATION.sub("", text))
    return " ".join(words), negative

@dataclass
class ClaimNode:
    id: str
    seat: str
    text: str
    confidence: int
    evidence_refs: list[str] = field(default_factory=list)

@dataclass
class EvidenceNode:
    id: str
    source: str
    content_hash: str
    snippet: str
    verified: bool

@dataclass
class ObjectionNode:
    id: str
    objecting_seat: str
    target_claim_id: str
    rationale: str
    status: str = "UNRESOLVED"

class ClaimGraph:
    def __init__(self, opinions=None, correlation_id=""):
        self.opinions = []
        self.claims = []
        self.evidence = []
        self.objections = []
        self.correlation_id = correlation_id
        for opinion in opinions or []:
            self.add_opinion(opinion)

    def add_opinion(self, opinion):
        self.opinions.append(opinion)
        for claim in opinion.claims:
            self.add_claim(ClaimNode(str(uuid4()), opinion.role, claim.text, claim.confidence))

    def add_claim(self, node):
        self.claims.append(node)

    def add_evidence(self, node):
        self.evidence.append(node)

    def add_objection(self, node):
        self.objections.append(node)

    def link_dialectical_turn(self, turn, opinions):
        if not turn.challenge_target or not turn.challenge_point:
            return
        target = turn.challenge_target.strip().casefold()
        roles = {o.role for o in opinions if target in (o.role.strip().casefold(), o.title.strip().casefold())}
        for claim in self.claims:
            if claim.seat in roles:
                self.add_objection(ObjectionNode(str(uuid4()), turn.seat_role, claim.id, turn.challenge_point))

    def get_contested_claims(self):
        active = {o.target_claim_id for o in self.objections if o.status.upper() == "UNRESOLVED"}
        return [asdict(c) for c in self.claims if c.id in active]

    def contradictions(self):
        found = []
        for a, b in combinations(self.claims, 2):
            if a.seat == b.seat:
                continue
            sa, na = _signature(a.text)
            sb, nb = _signature(b.text)
            if sa and sa == sb and na != nb:
                found.append({"seat_a": a.seat, "claim_a": a.text, "seat_b": b.seat, "claim_b": b.text})
        return found

    def consensus_score(self):
        if not self.opinions:
            return 0.0
        counts = Counter()
        for opinion in self.opinions:
            counts[opinion.stance.value] += getattr(opinion, "calibration_weight", 1.0)
        total = sum(counts.values())
        return max(counts.values()) / total if total else 0.0

    def to_dict(self):
        return {"correlation_id": self.correlation_id, "claims": [asdict(c) for c in self.claims],
                "evidence": [asdict(e) for e in self.evidence], "objections": [asdict(o) for o in self.objections],
                "contested_claims": self.get_contested_claims(), "contradictions": self.contradictions(),
                "consensus_score": self.consensus_score(),
                "seat_weights": {o.role: getattr(o, "calibration_weight", 1.0) for o in self.opinions}}
