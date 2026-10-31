"""Produce independent descendants that repair identified contract failures."""
from copy import deepcopy
import re
from uuid import uuid4
from .models import IdeaStatus, VerificationLevel


class EvolutionaryMutator:
    def mutate(self, idea, failure_reason):
        if idea.iteration_depth >= 3:
            raise ValueError('maximum mutation depth reached')
        child = deepcopy(idea)
        child.id = str(uuid4())
        child.iteration_depth += 1
        child.status = IdeaStatus.PROPOSED
        child.verification_level = VerificationLevel.HYPOTHESIS
        child.falsification_reason = ''
        reason = failure_reason.lower()
        if 'capital risk' in reason:
            child.invariant_contract.max_capital_risk_usd = 0.0
            child.invariant_contract.preconditions.append('Test using isolated replay with no capital at risk')
        elif 'latency budget' in reason:
            child.invariant_contract.max_latency_budget_ns = max(0, child.invariant_contract.max_latency_budget_ns)
        elif 'search' in reason:
            child.invariant_contract.complexity_time = 'O(n)'
            self._replace(child, r'o\s*\(\s*1\s*\)', 'O(n)')
        elif 'speed of light' in reason or 'wan latency' in reason:
            self._replace(child, r'zero[ -]latency', 'finite latency')
            self._replace(child, r'((?:wan\s*)?latency\s*[:=]?\s*)\d+(?:\.\d+)?\s*(?:ns|us|µs|ms|s)\b', r'\1subject to the fiber propagation bound')
            child.invariant_contract.preconditions.append('WAN latency must meet the fiber propagation bound')
        elif 'sharpe' in reason:
            self._replace(child, r'(?:zero|no|without)[ -]+(?:tail[ -]+)?risk|risk[ -]*free', 'measured tail risk')
        return child

    @staticmethod
    def _replace(idea, pattern, replacement):
        for name in ('title', 'problem_statement', 'baseline_reference', 'cheapest_falsification_test'):
            setattr(idea, name, re.sub(pattern, replacement, getattr(idea, name), flags=re.I))
        mechanism = idea.causal_mechanism
        if isinstance(mechanism, str):
            idea.causal_mechanism = re.sub(pattern, replacement, mechanism, flags=re.I)
        else:
            for name in ('trigger_event', 'causal_node', 'intervention', 'predicted_outcome', 'falsification_metric'):
                if hasattr(mechanism, name):
                    setattr(mechanism, name, re.sub(pattern, replacement, getattr(mechanism, name), flags=re.I))
        contract = idea.invariant_contract
        for name in ('preconditions', 'postconditions'):
            setattr(contract, name, [re.sub(pattern, replacement, x, flags=re.I) for x in getattr(contract, name)])
