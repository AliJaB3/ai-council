import ast
import math
import subprocess

import pytest

from ai_council.engine.router import DeliberationRouter, RouteType, VoIEngine
from ai_council.engine.crypto_commit import CommitRevealManager
from ai_council.engine.sandbox_runner import ASTPolicyViolation, ASTSecurityGate, IsolatedSandboxRunner
from ai_council.engine.brier_calibration import BrierEngine
from ai_council.engine.orchestrator import CouncilOrchestrator
from ai_council.models import Claim, CouncilVerdict, SeatOpinion
from ai_council.store.database import Database
from ai_council.cli import main


def test_routing_and_value_of_information():
    router = DeliberationRouter()
    assert router.route('What is the current status?') == RouteType.FAST_PATH
    assert router.route('Compare architecture trade-offs and risk') == RouteType.DEEP_PATH
    assert router.route('What is the status?', {'deep': True}) == RouteType.DEEP_PATH
    assert not VoIEngine().should_stop([0.5])
    assert VoIEngine().should_stop([0.5, 0.47])
    assert not VoIEngine().should_stop([0.5, 0.6])


def test_commit_reveal():
    manager = CommitRevealManager()
    digest = manager.generate_commitment({'b': 2, 'a': 1}, 'nonce')
    assert manager.verify_reveal(digest, {'a': 1, 'b': 2}, 'nonce')
    assert not manager.verify_reveal(digest, {'a': 2, 'b': 2}, 'nonce')
    assert not manager.verify_reveal(digest, {'a': 1, 'b': 2}, 'other')


def test_sandbox_gate_and_timeout():
    gate = ASTSecurityGate()
    gate.visit(ast.parse('import math\nprint(math.sqrt(9))'))
    for code in ('import os', 'from subprocess import run', 'eval("1")', '(1).__class__', '__import__("os")'):
        with pytest.raises(ASTPolicyViolation):
            gate.validate(code)
    assert IsolatedSandboxRunner().run('print(2 + 2)').stdout.strip() == '4'
    with pytest.raises(subprocess.TimeoutExpired):
        IsolatedSandboxRunner(timeout=0.1).run('while True: pass')


def test_brier_persistence_and_weights(tmp_path):
    path = tmp_path / 'scores.sqlite'
    brier = BrierEngine(path)
    for i in range(5):
        brier.record_forecast('seat', str(i), 0.8, 'run')
        brier.resolve_outcome(str(i), 1)
        if i < 4:
            assert brier.get_seat_weight('seat') == 1.0
    assert brier.compute_brier_score('seat') == pytest.approx(0.04)
    assert brier.get_seat_weight('seat') == pytest.approx(math.exp(-0.08))
    with pytest.raises(ValueError): brier.record_forecast('seat', 'bad', 1.1, 'run')
    with pytest.raises(ValueError): brier.resolve_outcome('0', 2)
    brier.close()
    reopened = BrierEngine(path)
    assert reopened.status()[0]['resolved'] == 5
    reopened.close()


def test_fast_integration_and_status(tmp_path, monkeypatch, capsys):
    class Seat:
        def evaluate(self, topic, grounding):
            return SeatOpinion('a', claims=[Claim('fact', confidence=8)])
        def cross_examine(self, *args):
            raise AssertionError('fast route must skip cross examination')
    class Arbiter:
        def synthesize(self, topic, opinions, turns, graph, grounding):
            assert len(opinions) == 1 and not turns
            return CouncilVerdict(topic=topic)
    path = tmp_path / 'council.sqlite'
    with Database(path) as store:
        verdict = CouncilOrchestrator(seats=[Seat(), Seat()], arbiter=Arbiter(), store=store).deliberate('What is the status?')
        record = store.get(verdict.id)
        assert verdict.audit_report['routing']['type'] == 'FAST_PATH'
        commitment = verdict.audit_report['commitments'][0]
        assert CommitRevealManager().verify_reveal(commitment['commitment'], record['opinions'][0], commitment['nonce'])
        claim_id = record['graph']['claims'][0]['id']
    brier = BrierEngine(path)
    brier.resolve_outcome(claim_id, 1)
    brier.close()
    monkeypatch.setenv('AI_COUNCIL_DB_PATH', str(path))
    assert main(['--brier-status']) == 0
    assert '0.0400' in capsys.readouterr().out
