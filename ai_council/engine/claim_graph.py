"""Claim relationships and an interpretable stance agreement score."""
import re
from itertools import combinations
from collections import Counter
from dataclasses import asdict

_NEGATION = re.compile(r"\b(?:not|never|no|cannot|can't|won't|doesn't|isn't|shouldn't)\b", re.I)
def _signature(text):
    text = text.lower().replace("can't", "can not").replace("won't", "will not").replace("doesn't", "does not").replace("isn't", "is not").replace("shouldn't", "should not")
    negative = bool(_NEGATION.search(text))
    words = re.findall(r"\w+", _NEGATION.sub("", text))
    return " ".join(words), negative

class ClaimGraph:
    def __init__(self, opinions=None):
        self.opinions = list(opinions or [])
    def add_opinion(self, opinion):
        self.opinions.append(opinion)
    def contradictions(self):
        found = []
        claims = [(o.role, c) for o in self.opinions for c in o.claims]
        for (role_a, a), (role_b, b) in combinations(claims, 2):
            if role_a == role_b:
                continue
            sa, na = _signature(a.text)
            sb, nb = _signature(b.text)
            if sa and sa == sb and na != nb:
                found.append({"seat_a": role_a, "claim_a": a.text, "seat_b": role_b, "claim_b": b.text})
        return found
    def consensus_score(self):
        if not self.opinions:
            return 0.0
        counts = Counter(o.stance.value for o in self.opinions)
        return max(counts.values()) / len(self.opinions)
    def to_dict(self):
        return {"claims": [{"seat": o.role, **asdict(c)} for o in self.opinions for c in o.claims], "contradictions": self.contradictions(), "consensus_score": self.consensus_score()}
