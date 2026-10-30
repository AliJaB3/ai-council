import sys
import pytest
from ai_council.engine.seal import CandidateGenerator, IsolatedSandboxRunner, RegressionEvaluator


def test_candidate_allowlist_and_protected_paths(tmp_path):
    (tmp_path / 'app.py').write_text('old\n')
    (tmp_path / 'other.py').write_text('old\n')
    (tmp_path / 'tests').mkdir()
    (tmp_path / 'tests' / 'test_a.py').write_text('pass\n')
    gen = CandidateGenerator(tmp_path, ['app.py'])
    assert '+new' in gen.generate({'app.py': 'new\n'})
    with pytest.raises(ValueError): gen.generate({'other.py': 'new\n'})
    with pytest.raises(ValueError): CandidateGenerator(tmp_path, ['tests/test_a.py'])
    with pytest.raises(ValueError): CandidateGenerator(tmp_path, ['../outside.py'])


def test_runner_fails_closed_without_isolation(tmp_path, monkeypatch):
    monkeypatch.setattr('ai_council.engine.seal.runner.shutil.which', lambda _: None)
    result = IsolatedSandboxRunner(tmp_path).run([sys.executable, '-c', 'pass'])
    assert result['status'] == 'FAILED'
    assert 'unavailable' in result['error']


class Runner:
    def __init__(self, outcomes): self.outcomes = iter(outcomes); self.calls = []
    def run(self, command, changes=None):
        self.calls.append(changes)
        return {'status': next(self.outcomes)}


def test_regression_evaluation():
    runner = Runner(['PASSED', 'FAILED'])
    result = RegressionEvaluator(runner, ['pytest']).evaluate({'app.py': 'changed'})
    assert result.verdict == 'REJECTED'
    assert runner.calls == [None, {'app.py': 'changed'}]
    runner = Runner(['FAILED'])
    assert RegressionEvaluator(runner, ['pytest']).evaluate({}).verdict == 'HARD_FAIL'
    assert len(runner.calls) == 1
    assert RegressionEvaluator(Runner(['PASSED', 'PASSED']), ['pytest']).evaluate({}).verdict == 'PROMOTABLE'
