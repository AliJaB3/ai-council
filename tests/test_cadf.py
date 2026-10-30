from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from ai_council.models import Claim, SeatOpinion, CouncilVerdict
from ai_council.engine.drift_auditor import DriftAuditor
from ai_council.engine.info_delphi import InfoDelphi
from ai_council.engine.armor_engine import ArmorEngine
from ai_council.engine.dag_router import DAGRouter
from ai_council.engine.orchestrator import CouncilOrchestrator
from ai_council.store.database import Database
from ai_council import cli

GROUND = [{'path': '/tmp/example.py', 'exists': True, 'content': 'def calculate():\n    return 42'}]

def opinion(role, text='calculate() returns 42'):
    return SeatOpinion(role=role, stance='SUPPORT', confidence=9, claims=[Claim(text)])

def test_audit_threshold_and_missing_references():
    auditor = DriftAuditor()
    result = auditor.audit([Claim('calculate() exists')] * 3 + [Claim('missing() exists')], GROUND)
    assert result.support_ratio == .75 and not result.kill_switch_triggered
    result = auditor.audit([Claim('calculate() exists'), Claim('missing.py calls nope()')], GROUND)
    assert result.status == 'DEFICIT' and result.kill_switch_triggered
    assert result.unsupported_details[0]['reason'].startswith('Missing references')

def test_blind_views_are_independent():
    barrier = Barrier(2)
    class Seat:
        def evaluate(self, topic, grounding):
            grounding[0]['content'] = topic
            barrier.wait()
            assert grounding[0]['content'] == topic
            return topic
    views = InfoDelphi()
    assert views.slice_evidence(GROUND * 2, 0, 2, True) == GROUND
    assert views.evaluate([Seat(), Seat()], 'private', GROUND)[0] == ['private', 'private']
    assert GROUND[0]['content'].startswith('def')

def test_armor_and_router():
    opinions = [opinion('a'), opinion('b')]
    armor = ArmorEngine()
    risk = armor.evaluate_consensus(opinions)
    assert risk['adversarial_injection_needed']
    assert DAGRouter().route(risk)['run_phase2']
    grounded = armor.evaluate_consensus(opinions, DriftAuditor().audit(opinions, GROUND))
    assert grounded['can_early_exit']
    assert DAGRouter().route(grounded, early_exit=True, deep=True)['early_exit']

def test_database_concurrent_access(tmp_path):
    with Database(tmp_path / 'test.sqlite') as db:
        def task(i):
            db.save(CouncilVerdict(id=str(i), topic=str(i), audit_report={'status': 'VALID'}))
            return db.get(str(i))['verdict']['audit_report']['status']
        with ThreadPoolExecutor(max_workers=8) as pool:
            assert list(pool.map(task, range(40))) == ['VALID'] * 40
        assert len(db.history()) == 40

def test_pipeline_and_cli_flags(tmp_path, monkeypatch, capsys):
    path = tmp_path / 'example.py'
    path.write_text(GROUND[0]['content'])
    class Seat:
        def __init__(self, role): self.role = role
        def evaluate(self, topic, grounding): return opinion(self.role)
        def cross_examine(self, topic, opinions): raise AssertionError('should skip')
    class Arbiter:
        def synthesize(self, topic, opinions, turns, graph, grounding): return CouncilVerdict(topic=topic)
    with Database(':memory:') as db:
        engine = CouncilOrchestrator(seats=[Seat('a'), Seat('b')], arbiter=Arbiter(), store=db)
        verdict = engine.deliberate('test', [str(path)], deep=True, early_exit=True)
        assert verdict.early_exit and verdict.audit_report['status'] == 'VALID'
        assert db.get(verdict.id)['verdict']['audit_report'] == verdict.audit_report
        class BadSeat(Seat):
            def evaluate(self, topic, grounding): return opinion(self.role, 'missing() exists')
        engine.seats = [BadSeat('a')]
        with pytest.raises(ValueError, match='Evidence deficit'):
            engine.deliberate('test', [str(path)], strict_audit=True)
    with pytest.raises(SystemExit) as exit_info:
        cli.main(['--help'])
    assert exit_info.value.code == 0
    help_text = capsys.readouterr().out
    assert all(flag in help_text for flag in ('--early-exit', '--audit', '--strict-audit'))
