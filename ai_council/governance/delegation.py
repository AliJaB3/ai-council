"""Cycle-free liquid delegation with a per-recipient credit cap."""
import math

class LiquidDelegation:
    def __init__(self):
        self.delegates = {}

    def delegate(self, voter, delegatee):
        current = delegatee
        seen = {voter}
        while current in self.delegates:
            if current in seen:
                raise ValueError('delegation cycle')
            seen.add(current)
            current = self.delegates[current]
        if current in seen:
            raise ValueError('delegation cycle')
        self.delegates[voter] = delegatee

    def resolve_effective_votes(self, base_credits):
        if any(not math.isfinite(v) or v < 0 for v in base_credits.values()):
            raise ValueError('credits must be finite and nonnegative')
        cap = sum(base_credits.values()) * 0.4
        totals = {}
        for voter, credits in base_credits.items():
            current, seen = voter, set()
            while current in self.delegates:
                if current in seen:
                    raise ValueError('delegation cycle')
                seen.add(current)
                current = self.delegates[current]
            totals[current] = totals.get(current, 0.0) + credits
        return {voter: min(credits, cap) for voter, credits in totals.items()}
