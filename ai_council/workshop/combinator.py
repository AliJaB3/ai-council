"""Generate structured candidates from a morphological matrix."""
from datetime import datetime, timezone
from itertools import product
from uuid import uuid4

from .models import IdeaCard
from ..skills.models import Domain


class MorphologicalCombinator:
    PROBLEMS = ['liquidity_fragmentation', 'flaky_concurrency', 'token_budget_exhaustion', 'sycophancy_in_debate', 'slippage_during_volatility']
    MECHANISMS = ['batch_auction', 'circuit_breaker', 'stratified_replay', 'adversarial_red_teaming', 'negative_constraint_pruning', 'zk_proof_verification']

    def combine(self, domain: Domain, count: int = 3) -> list[IdeaCard]:
        pairs = list(product(self.PROBLEMS, self.MECHANISMS))
        if count < 0 or count > len(pairs):
            raise ValueError(f'count must be between 0 and {len(pairs)}')
        # Spread early candidates across both dimensions.
        pairs.sort(key=lambda pair: (self.PROBLEMS.index(pair[0]) + self.MECHANISMS.index(pair[1]), self.PROBLEMS.index(pair[0])))
        ideas = []
        for problem, mechanism in pairs[:count]:
            p, m = problem.replace('_', ' '), mechanism.replace('_', ' ')
            ideas.append(IdeaCard(
                id=str(uuid4()), title=f'{m.title()} for {p}', domain=domain,
                problem_statement=f'Reduce {p} in the {domain.value} domain.',
                causal_mechanism=f'Apply {m} to {p}; measure whether the intervention improves the outcome.',
                baseline_reference=f'Existing approach to {p} without {m}.',
                cheapest_falsification_test=f'Compare {m} with the baseline on a small, representative replay; reject if the outcome does not improve.',
                created_at=datetime.now(timezone.utc).isoformat(),
            ))
        return ideas


class HyperPrecisionCombinator:
    """Transpose a source domain's mechanisms onto target-domain problems."""
    def __init__(self, registry=None):
        from .registry import DimensionRegistry
        self.registry = registry or DimensionRegistry()

    def combine(self, domain, count=3):
        from .models import Domain as WorkshopDomain, CausalMechanism, InvariantContract
        domain = WorkshopDomain(domain)
        if count < 0:
            raise ValueError('count must be non-negative')
        pack = self.registry.get(domain)
        problems = pack['problems'] or ['unmeasured system performance']
        sources = [(d, p) for d, p in self.registry.packs.items() if d != domain and p['mechanisms']]
        if not sources:
            raise ValueError('at least one source domain with mechanisms is required')
        combinations = [(problem, d, mechanism, primitive) for problem in problems for d, p in sources for mechanism in p['mechanisms'] for primitive in (p['primitives'] or ['system behavior'])]
        if count > len(combinations):
            raise ValueError(f'count must be between 0 and {len(combinations)}')
        ideas = []
        for problem, source, mechanism, primitive in combinations[:count]:
            ideas.append(IdeaCard(
                id=str(uuid4()), title=f'{mechanism.title()} for {problem}', domain=domain,
                secondary_domains=[source], problem_statement=f'Reduce {problem} in {domain.value}.',
                causal_mechanism=CausalMechanism(problem, primitive, f'Adapt {mechanism} from {source.value}', f'Reduce {problem} relative to baseline', 'relative improvement', 0.0),
                invariant_contract=InvariantContract(preconditions=['Use isolated replay with no capital at risk'], postconditions=['Compare against the baseline'], complexity_time='O(n)', complexity_space='O(n)'),
                baseline_reference=f'Existing approach to {problem}.',
                cheapest_falsification_test=f'Compare against baseline on a representative replay; reject if {problem} does not improve.',
                created_at=datetime.now(timezone.utc).isoformat()))
        return ideas
