from dataclasses import replace
import pytest
from ai_council.workshop import (Domain, IdeaStatus, DimensionRegistry, HyperPrecisionCombinator,
    MultiDomainCrucible, EvolutionaryMutator, AutonomousCrucibleWorkshop)
from ai_council.cli import main


@pytest.fixture
def idea():
    return HyperPrecisionCombinator().combine(Domain.BINANCE_ALGO, 1)[0]


def test_axioms(idea):
    audit = MultiDomainCrucible()
    idea.problem_statement = 'WAN latency 1 ms over distance 1000 km'
    assert audit.audit(idea).status == IdeaStatus.TIER_0_REJECTED
    idea.problem_statement = 'WAN latency 5 ms over distance 1000 km'
    assert audit.audit(idea).status == IdeaStatus.VALIDATED
    idea.problem_statement = 'Sharpe ratio of 5 without tail risk'
    assert audit.audit(idea).status == IdeaStatus.TIER_0_REJECTED
    idea.problem_statement = 'Sharpe ratio of 5 with measured tail risk'
    assert audit.audit(idea).status == IdeaStatus.VALIDATED
    idea.problem_statement = 'O(1) search on unindexed arbitrary datasets'
    assert audit.audit(idea).status == IdeaStatus.TIER_0_REJECTED


def test_contract_and_mutation(idea):
    audit, mutator = MultiDomainCrucible(), EvolutionaryMutator()
    idea.invariant_contract.max_capital_risk_usd = 10
    idea.invariant_contract.max_latency_budget_ns = -1
    assert audit.audit(idea).status == IdeaStatus.TIER_1_REJECTED
    child = mutator.mutate(idea, idea.falsification_reason)
    assert idea.invariant_contract.max_capital_risk_usd == 10
    assert audit.audit(child).status == IdeaStatus.TIER_1_REJECTED
    child = mutator.mutate(child, child.falsification_reason)
    assert audit.audit(child).status == IdeaStatus.VALIDATED
    assert child.iteration_depth == 2
    with pytest.raises(ValueError):
        mutator.mutate(replace(child, iteration_depth=3), 'anything')


def test_registry_cycle_and_cli(capsys):
    registry = DimensionRegistry()
    registry.register(Domain.AI_MODELS, problems=['drift'], primitives=['tokens'], mechanisms=['sampling'])
    workshop = AutonomousCrucibleWorkshop(count=2, registry=registry)
    result = workshop.run_cycle('models', Domain.AI_MODELS)
    assert len(result) == 2 and all(x.domain == Domain.AI_MODELS and x.secondary_domains for x in result)
    assert main(['trading', '--workshop', '--workshop-domain', 'binance_algo', '--workshop-count', '1']) == 0
    out = capsys.readouterr().out
    assert '[AXIOMATIC: PASS]' in out and '[CONTRACT: PASS]' in out and '[STATUS: VALIDATED]' in out
