import math
import subprocess

import pytest

from ai_council.engine.streaming import DeliberationEventStream
from ai_council.engine.lmsr_market import LMSRShadowMarket
from ai_council.engine.git_fork import CounterfactualForkManager
from ai_council.engine.pareto_scaler import ParetoScaler


def test_stream_order_and_filter():
    stream = DeliberationEventStream()
    received = []
    stream.subscribe(received.append)
    first = stream.emit('START', 'a', {'x': 1})
    second = stream.emit('END', 'b', {})
    assert received == [first, second]
    assert [e.seq for e in received] == [1, 2]
    assert stream.get_history('a') == [first]
    assert first.event_id != second.event_id


def test_market_cost_probability_and_settlement():
    market = LMSRShadowMarket()
    state = market.open_market('c', 'session', 100)
    assert state['cost'] == pytest.approx(100 * math.log(2))
    state = market.place_bet('c', 'alice', 'YES', 10)
    assert state['probability_yes'] == pytest.approx(1 / (1 + math.exp(-0.1)))
    assert state['probability_yes'] + state['probability_no'] == pytest.approx(1)
    result = market.settle('c', True)
    assert result['payoffs']['alice'] > 0
    assert result['brier_score'] == 0
    with pytest.raises(ValueError):
        market.place_bet('c', 'bob', 'NO', 5)


def test_fork_runs_and_cleans(tmp_path):
    def git(*args):
        return subprocess.run(['git', '-C', str(tmp_path), *args], check=True, capture_output=True, text=True)
    git('init')
    git('config', 'user.email', 'test@example.com')
    git('config', 'user.name', 'Test')
    (tmp_path / 'code.py').write_text('value = 1\n')
    git('add', 'code.py')
    git('commit', '-m', 'initial')
    receipt = CounterfactualForkManager().fork_and_test(str(tmp_path), {'code.py': 'value = 2\n'}, "python -c 'import code; assert code.value == 2'", 'id')
    assert receipt.status == 'PASSED', receipt.stdout
    assert (tmp_path / 'code.py').read_text() == 'value = 1\n'
    assert receipt.branch_name not in git('branch', '--list').stdout
    assert len(git('worktree', 'list', '--porcelain').stdout.strip().split('worktree ')) == 2
    assert CounterfactualForkManager().fork_and_test(str(tmp_path), {'../bad.py': 'x=1'}, 'true', 'id').status == 'SECURITY_VIOLATION'


def test_pareto_budget():
    scaler = ParetoScaler()
    simple = scaler.compute_budget('Simple question', False)
    complex_budget = scaler.compute_budget('Design distributed architecture', False)
    deep = scaler.compute_budget('Simple question', True)
    assert simple['max_rounds'] == 1
    assert complex_budget['max_rounds'] == deep['max_rounds'] == 2
    assert simple['token_budget'] < complex_budget['token_budget'] < deep['token_budget']
