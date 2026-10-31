"""Consensus assessment and premature agreement detection."""
from collections import Counter
from math import log2
from ..models import Stance

class ArmorEngine:
    def evaluate_consensus(self, opinions, audit_result=None):
        counts = Counter()
        for o in opinions:
            counts[o.stance.value if isinstance(o.stance, Stance) else str(o.stance)] += getattr(o, "calibration_weight", 1.0)
        n = sum(counts.values())
        entropy = -sum((v/n) * log2(v/n) for v in counts.values()) if n else 0.0
        unanimous = len(opinions) > 1 and len(counts) == 1
        high_confidence = unanimous and all(o.confidence >= 8 for o in opinions)
        grounded = bool(audit_result and audit_result.total_claims > 0 and not audit_result.kill_switch_triggered and audit_result.unsupported_claims == 0 and all(o.claims for o in opinions))
        risk = bool(high_confidence and not grounded)
        return {'stance_distribution': dict(counts), 'consensus_entropy': entropy,
                'sycophancy_risk': risk, 'adversarial_injection_needed': risk,
                'can_early_exit': bool(high_confidence and grounded), 'conflict': len(counts) > 1}
