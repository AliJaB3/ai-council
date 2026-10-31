import hashlib
import json
from types import SimpleNamespace

from ai_council.cli import main
from ai_council.contracts.records import MemoryRecord, TrustState
from ai_council.engine.evomem import EvoMemStore, QuarantineManager
from ai_council.engine.orchestrator import CouncilOrchestrator
from ai_council.engine.router import VoIEngine
from ai_council.models import Claim, CouncilVerdict, SeatOpinion
from ai_council.store.database import Database


def memory_record():
    content = 'verified evidence'
    return MemoryRecord(payload={'topic': 'test'}, tenant_id='default', session_id='session',
                        evidence_refs=[{'content': content, 'sha256': hashlib.sha256(content.encode()).hexdigest()}])


def test_dissent_guard():
    engine = VoIEngine()
    assert not engine.should_stop([0, 0], unresolved_objections=1)
    assert engine.should_stop([0, 0], unresolved_objections=0)
    assert not engine.should_stop([0], unresolved_objections=0)


def test_promotion_and_regression():
    with EvoMemStore(':memory:') as store:
        manager = QuarantineManager(store)
        accepted = manager.propose(memory_record())
        rejected = manager.propose(memory_record())
        assert manager.promote(accepted)
        assert store._get(accepted).trust_state == TrustState.VALIDATED
        assert not manager.promote(rejected, regression_passed=False)
        assert store._get(rejected).trust_state == TrustState.REVOKED
        assert not manager.promote(rejected)


def test_weights_reach_synthesis_and_verdict(tmp_path):
    class Seat:
        config = SimpleNamespace(role='architect')
        def evaluate(self, topic, grounding):
            return SeatOpinion('architect', claims=[Claim('fact')])
    class Calibration:
        def get_seat_weight(self, role): return 0.4
        def record_forecast(self, *args): pass
    class Arbiter:
        def synthesize(self, topic, opinions, turns, graph, grounding):
            assert opinions[0].calibration_weight == 0.4
            assert graph['seat_weights'] == {'architect': 0.4}
            return CouncilVerdict(topic=topic)
    with Database(tmp_path / 'db') as store:
        result = CouncilOrchestrator(seats=[Seat()], arbiter=Arbiter(), store=store,
                                     brier_engine=Calibration()).deliberate('What is the status?')
        assert result.seat_weights == {'architect': 0.4}
        assert store.get(result.id)['verdict']['seat_weights'] == result.seat_weights


def test_cli_promotion_and_brier_status(tmp_path, monkeypatch, capsys):
    path = tmp_path / 'council.sqlite'
    monkeypatch.setenv('AI_COUNCIL_DB_PATH', str(path))
    with EvoMemStore(path.with_suffix('.evomem.sqlite')) as store:
        record_id = store.propose(memory_record())
    assert main(['--promote-memory', record_id, '--brier-status', '--json']) == 0
    output = json.loads(capsys.readouterr().out)
    assert output['memory_promoted'] == record_id
    assert output['brier_status']
    with EvoMemStore(path.with_suffix('.evomem.sqlite')) as store:
        assert store._get(record_id).trust_state == TrustState.VALIDATED
