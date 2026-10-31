"""Conservative checks for explicitly stated physical and contract violations.

Passing these checks is not empirical proof of an idea's claims.
"""
import math
import re
from dataclasses import asdict
from .models import IdeaStatus


def _text(idea):
    data = asdict(idea)
    for key in ('status', 'falsification_reason', 'verification_level'):
        data.pop(key, None)
    return str(data).lower()


class MultiDomainCrucible:
    def audit_tier_0_axiomatic(self, idea):
        text = _text(idea)
        if re.search(r'(?:wan|wide.area.network).*zero[ -]latency|zero[ -]latency.*(?:wan|wide.area.network)', text):
            return False, 'WAN latency cannot be zero (speed of light in fiber).'
        distance = re.search(r'(?:distance\s*[:=]?\s*)?(\d+(?:\.\d+)?)\s*km', text)
        latency = re.search(r'(?:wan\s*)?latency\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(ns|us|µs|ms|s)\b', text)
        if distance and latency and ('wan' in text or 'wide area' in text):
            seconds = float(latency.group(1)) * {'ns': 1e-9, 'us': 1e-6, 'µs': 1e-6, 'ms': 1e-3, 's': 1}[latency.group(2)]
            if seconds < float(distance.group(1)) / 200_000 or seconds == 0:
                return False, 'WAN latency violates the speed of light in fiber.'
        sharpe = re.findall(r'sharpe(?:\s+ratio)?\s*(?:of|is|=|:|>|at)?\s*(\d+(?:\.\d+)?)', text)
        metric = idea.metrics.get('sharpe', idea.metrics.get('sharpe_ratio', 0))
        try:
            high = float(metric) > 4.5 or any(float(x) > 4.5 for x in sharpe)
        except (ValueError, TypeError):
            high = any(float(x) > 4.5 for x in sharpe)
        if high and re.search(r'(?:zero|no|without)[ -]+(?:tail[ -]+)?risk|risk[ -]*free', text):
            return False, 'Sharpe above 4.5 without tail risk is implausible.'
        if re.search(r'o\s*\(\s*1\s*\)', text) and re.search(r'(?:search|lookup)', text) and re.search(r'unindexed|arbitrary', text) and not re.search(r'indexed dataset', text.replace('unindexed dataset', '')):
            return False, 'O(1) search of an unindexed arbitrary dataset is impossible.'
        return True, ''

    def audit_tier_1_contract(self, idea):
        contract = idea.invariant_contract
        if not math.isfinite(contract.max_capital_risk_usd) or contract.max_capital_risk_usd != 0:
            return False, 'Capital risk during the test must be $0.00.'
        if not math.isfinite(contract.max_latency_budget_ns) or contract.max_latency_budget_ns < 0:
            return False, 'Latency budget must be non-negative.'
        return True, ''

    def audit(self, idea):
        ok, reason = self.audit_tier_0_axiomatic(idea)
        if not ok:
            idea.status, idea.falsification_reason = IdeaStatus.TIER_0_REJECTED, reason
            return idea
        ok, reason = self.audit_tier_1_contract(idea)
        idea.status = IdeaStatus.VALIDATED if ok else IdeaStatus.TIER_1_REJECTED
        idea.falsification_reason = reason
        return idea
