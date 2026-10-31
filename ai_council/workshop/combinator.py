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
