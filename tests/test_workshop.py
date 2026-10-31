from dataclasses import replace

import pytest

from ai_council.cli import main
from ai_council.skills.models import Domain
from ai_council.workshop import (
    Anomaly, FalsificationInquisitor, IdeaStatus, IdeationWorkshop,
    MorphologicalCombinator,
)


def test_combinations_are_structured_and_distinct():
    ideas = MorphologicalCombinator().combine(Domain.FINANCE, 8)
    assert len(ideas) == len({idea.title for idea in ideas}) == 8
    assert all(idea.domain == Domain.FINANCE and idea.causal_mechanism and idea.baseline_reference and idea.cheapest_falsification_test for idea in ideas)
    assert all(idea.status == IdeaStatus.PROPOSED and idea.created_at for idea in ideas)
    with pytest.raises(ValueError):
        MorphologicalCombinator().combine(Domain.GENERAL, 31)


@pytest.mark.parametrize('claim', ['Sharpe ratio of 4.6', 'zero latency over WAN', 'guaranteed alpha', 'O(1) arbitrary search', 'unbounded blast radius'])
def test_rejects_implausible_claims(claim):
    idea = MorphologicalCombinator().combine(Domain.GENERAL, 1)[0]
    idea.causal_mechanism = claim
    result = FalsificationInquisitor().audit(idea)
    assert result.status == IdeaStatus.FALSIFIED
    assert result.falsification_reason


def test_audit_viable_and_metrics():
    idea = MorphologicalCombinator().combine(Domain.FINANCE, 1)[0]
    auditor = FalsificationInquisitor()
    assert auditor.audit(idea).status == IdeaStatus.VALIDATED
    idea.metrics['sharpe'] = 5
    assert auditor.audit(idea).status == IdeaStatus.FALSIFIED
    idea.metrics['sharpe'] = 4.5
    assert auditor.audit(idea).status == IdeaStatus.VALIDATED
    assert not idea.falsification_reason


def test_cycle_detects_domain_and_includes_anomalies():
    anomaly = Anomaly('a1', 'exchange', 'slippage', 3.2, {}, '2026-01-01')
    workshop = IdeationWorkshop(count=2)
    ideas = workshop.run_cycle('reduce trading slippage', seed_anomalies=[anomaly])
    assert len(ideas) == 2
    assert all(i.domain == Domain.FINANCE and i.metrics['seed_anomaly_ids'] == ['a1'] for i in ideas)
    assert all('exchange: slippage' in i.problem_statement for i in ideas)
    assert workshop.run_cycle('trading', domain=Domain.SECURITY)[0].domain == Domain.SECURITY


def test_cycle_filters_rejected_candidates():
    workshop = IdeationWorkshop()
    idea = MorphologicalCombinator().combine(Domain.GENERAL, 1)[0]
    workshop.combinator.combine = lambda domain, count: [replace(idea, title='guaranteed alpha')]
    assert workshop.run_cycle('test') == []
    assert workshop.candidates[0].status == IdeaStatus.FALSIFIED


def test_cli_workshop(capsys):
    assert main(['trading', '--workshop', '--workshop-count', '2']) == 0
    output = capsys.readouterr().out
    assert output.count('[VALIDATED]') == 2
    assert 'Mechanism:' in output and 'Cheapest falsification test:' in output
