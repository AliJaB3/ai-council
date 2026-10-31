import json

import pytest

from ai_council.cli import main
from ai_council.engine.claim_graph import ClaimGraph, ClaimNode, EvidenceNode, ObjectionNode
from ai_council.engine.experiment_spec import ExperimentSpecGenerator
from ai_council.engine.orchestrator import CouncilOrchestrator
from ai_council.models import Claim, CouncilVerdict, DialecticTurn, SeatOpinion
from ai_council.store.database import Database


def test_graph_links_active_objections():
    opinion = SeatOpinion('architect', title='Architect', claims=[Claim('The design scales')])
    graph = ClaimGraph([opinion])
    graph.add_claim(ClaimNode('extra', 'other', 'Another claim', 7, ['e']))
    graph.add_evidence(EvidenceNode('e', 'source', 'hash', 'snippet', True))
    graph.link_dialectical_turn(DialecticTurn('reviewer', challenge_target='Architect', challenge_point='Measure it'), [opinion])
    graph.add_objection(ObjectionNode('resolved', 'reviewer', 'extra', 'Old issue', 'RESOLVED'))
    result = graph.to_dict()
    assert len(result['objections']) == 2
    assert [c['text'] for c in result['contested_claims']] == ['The design scales']
    assert result['evidence'][0]['verified']


def test_experiment_template_is_executable_and_requires_measurement():
    generator = ExperimentSpecGenerator()
    assert generator.generate('topic', [], 'thread') is None
    spec = generator.generate('topic', [{'text': 'It scales'}], 'thread')
    assert spec.correlation_id == 'thread' and spec.pass_threshold == 1.0
    namespace = {}
    exec(compile(spec.test_code_template, '<experiment>', 'exec'), namespace)
    with pytest.raises(NotImplementedError):
        namespace['test_contested_claims']()
    namespace['measure_support'] = lambda: 1.0
    namespace['test_contested_claims']()
    namespace['measure_support'] = lambda: 0.5
    with pytest.raises(AssertionError):
        namespace['test_contested_claims']()


def test_deliberation_persists_thread_and_cli(tmp_path, monkeypatch, capsys):
    source = tmp_path / 'evidence.txt'
    source.write_text('Measured throughput')

    class Seat:
        def __init__(self, role): self.role = role
        def evaluate(self, topic, grounding):
            return SeatOpinion(self.role, claims=[Claim('Measured throughput', source=str(source))])
        def cross_examine(self, topic, opinions):
            return DialecticTurn(self.role, challenge_target='a', challenge_point='Measure throughput')

    class Arbiter:
        def synthesize(self, topic, opinions, turns, graph, grounding):
            assert all(o.correlation_id == graph['correlation_id'] for o in opinions)
            return CouncilVerdict(topic=topic)

    db = tmp_path / 'council.sqlite'
    with Database(db) as store:
        verdict = CouncilOrchestrator(seats=[Seat('a'), Seat('b')], arbiter=Arbiter(), store=store).deliberate('throughput', [source], deep=True)
        record = store.get(verdict.id)
        assert record['verdict']['correlation_id'] == record['graph']['correlation_id'] == verdict.correlation_id
        assert record['verdict']['experiment_spec']['correlation_id'] == verdict.correlation_id
        assert record['graph']['claims'][0]['evidence_refs'] == [record['graph']['evidence'][0]['id']]
    monkeypatch.setenv('AI_COUNCIL_DB_PATH', str(db))
    assert main(['--history', '--emit-experiment']) == 0
    output = capsys.readouterr().out
    assert 'CEO Graph:' in output and verdict.correlation_id in output and 'Hypothesis:' in output
    assert main(['--history', '--emit-experiment', '--json']) == 0
    assert json.loads(capsys.readouterr().out)['history'][0]['verdict']['experiment_spec']['spec_id']
