import json
import sqlite3
from dataclasses import asdict, replace

import httpx
import pytest

from ai_council.config import Settings, SEATS
from ai_council.models import Claim, SeatOpinion, DialecticTurn, CouncilVerdict, Stance
from ai_council.seats import BaseSeat, SeatError
from ai_council.engine.claim_graph import ClaimGraph
from ai_council.engine.grounding import snapshot_file, changed
from ai_council.engine.orchestrator import CouncilOrchestrator
from ai_council.store import Database
from ai_council.cli import main


def test_models_validation():
    opinion = SeatOpinion(role='x', stance='support', claims=[{'text': 'yes'}])
    assert opinion.stance is Stance.SUPPORT
    assert isinstance(opinion.claims[0], Claim)
    with pytest.raises(ValueError): Claim('x', confidence=11)
    with pytest.raises(ValueError): SeatOpinion(role='x', stance='unknown')


def test_claim_graph():
    a = SeatOpinion('a', stance='SUPPORT', claims=[Claim('The system is safe')])
    b = SeatOpinion('b', stance='OPPOSE', claims=[Claim('The system is not safe')])
    graph = ClaimGraph([a, b])
    assert len(graph.contradictions()) == 1
    assert graph.consensus_score() == .5
    assert ClaimGraph().consensus_score() == 0


def test_grounding_changes(tmp_path):
    path = tmp_path / 'file.txt'
    path.write_text('one')
    snap = snapshot_file(path)
    assert snap['content'] == 'one' and not changed(snap)
    path.write_text('two')
    assert changed(snap)
    path.unlink()
    assert changed(snap)


def test_store_search_and_stale(tmp_path):
    path = tmp_path / 'input'
    path.write_text('hello')
    db = tmp_path / 'db.sqlite'
    with Database(db) as store:
        assert store.connection.execute('pragma journal_mode').fetchone()[0] == 'wal'
        verdict = CouncilVerdict(topic='Design storage', executive_verdict='Use durable writes')
        store.save(verdict, grounding=[snapshot_file(path)])
        assert store.search('durable')[0]['verdict']['id'] == verdict.id
        assert store.search('missing') == []
        assert store.history()[0]['verdict']['topic'] == verdict.topic
        assert store.check_stale() == []
        path.write_text('changed')
        assert store.check_stale() == [verdict.id]
        assert store.get(verdict.id)['verdict']['status'] == 'STALE'
        assert store.check_stale() == []
    with Database(db) as store:
        assert store.get(verdict.id)['verdict']['status'] == 'STALE'


def test_existing_tables_preserved(tmp_path):
    path = tmp_path / 'old.sqlite'
    conn = sqlite3.connect(path)
    conn.execute('create table decisions (id text, topic text)')
    conn.execute('insert into decisions values (?, ?)', ('old', 'legacy'))
    conn.commit(); conn.close()
    with Database(path) as store:
        assert store.connection.execute('select topic from decisions').fetchone()[0] == 'legacy'


def test_seat_http_fallback():
    calls = []
    def handler(request):
        payload = json.loads(request.content)
        calls.append(payload['model'])
        if len(calls) == 1: return httpx.Response(503)
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({'stance': 'SUPPORT', 'confidence': 8, 'claims': [{'text': 'works'}]})}}]})
    client = httpx.Client(transport=httpx.MockTransport(handler))
    seat = BaseSeat(SEATS[2], Settings(), client)
    opinion = seat.evaluate('topic')
    assert calls == ['antigravity/claude-sonnet-4-6', 'zro/glm-5.3-flash']
    assert opinion.model_used == 'zro/glm-5.3-flash' and opinion.claims[0].text == 'works'
    client.close()


@pytest.mark.parametrize('model,has_format,compact', [
    ('groq/model', False, False),
    ('cerebras/model', False, False),
    ('cloudflare-playground/model', True, True),
    ('unorouter/model', True, True),
    ('zro/model', True, False),
])
def test_provider_request_options(model, has_format, compact):
    requests = []
    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={'choices': [{'message': {'content': '{}'}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        seat = BaseSeat(replace(SEATS[0], model=model, fallbacks=()), Settings(), client)
        payload = {'topic': 'a' * 6000}
        seat._ask('instruction', payload)
    request = requests[0]
    assert ('response_format' in request) is has_format
    content = request['messages'][1]['content']
    original = json.dumps(payload)
    if compact:
        assert content == original[:3800] + '\n\n[...context compacted to fit provider limits...]\n\n' + original[-1400:]
        assert len(content) < 5500
    else:
        assert content == original


def test_seat_errors():
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(500)))
    with pytest.raises(SeatError): BaseSeat(SEATS[0], Settings(), client).evaluate('topic')
    client.close()


def test_seat_urllib_fallback(monkeypatch):
    from io import BytesIO
    from urllib.error import URLError
    from ai_council.seats import base

    calls = []
    def open_request(request, timeout):
        calls.append(json.loads(request.data))
        assert request.full_url == 'http://example.test/v1/chat/completions'
        assert request.get_header('Authorization') == 'Bearer secret'
        assert request.get_header('Content-type') == 'application/json'
        assert timeout == SEATS[2].timeout
        if len(calls) == 1:
            raise URLError('offline')
        return BytesIO(json.dumps({'choices': [{'message': {'content': '{"stance": "SUPPORT"}'}}]}).encode())

    monkeypatch.setattr(base, 'httpx', None)
    monkeypatch.setattr(base, 'urlopen', open_request)
    opinion = BaseSeat(SEATS[2], Settings(base_url='http://example.test/v1/', api_key='secret')).evaluate('topic')
    assert [call['model'] for call in calls] == [SEATS[2].model, SEATS[2].fallbacks[0]]
    assert opinion.model_used == SEATS[2].fallbacks[0]


class FakeSeat:
    def __init__(self, role, fail=False): self.role, self.fail = role, fail
    def evaluate(self, topic, grounding):
        if self.fail: raise SeatError('offline')
        return SeatOpinion(self.role, stance='SUPPORT', claims=[Claim('test claim')])
    def cross_examine(self, topic, opinions): return DialecticTurn(self.role, text='challenge')

class FakeArbiter:
    def synthesize(self, topic, opinions, turns, graph, grounding):
        assert opinions and graph['claims']
        return CouncilVerdict(topic=topic, executive_verdict=f'{len(turns)} turns')


def test_orchestration_and_cli(tmp_path, monkeypatch, capsys):
    db = tmp_path / 'db.sqlite'
    with Database(db) as store:
        engine = CouncilOrchestrator(seats=[FakeSeat('a'), FakeSeat('b', True)], arbiter=FakeArbiter(), store=store)
        result = engine.deliberate('Test proposal', deep=True)
        assert result.status == 'PARTIAL'
        assert result.executive_verdict == '2 turns'
        assert len(store.get(result.id)['opinions']) == 1
    monkeypatch.setenv('AI_COUNCIL_DB_PATH', str(db))
    assert main(['--search', 'proposal', '--json']) == 0
    assert json.loads(capsys.readouterr().out)['search'][0]['verdict']['id'] == result.id
    assert main(['--check-stale', '--json']) == 0
    assert json.loads(capsys.readouterr().out)['stale'] == []


def test_all_failed_and_missing(tmp_path):
    engine = CouncilOrchestrator(seats=[FakeSeat('bad', True)], arbiter=FakeArbiter())
    with pytest.raises(SeatError): engine.run('topic')
    with pytest.raises(FileNotFoundError): engine.run('topic', [tmp_path / 'missing'])


def test_json_object_extracts_model_response():
    from ai_council.seats.base import _json_object
    assert _json_object('<think>ignore {"bad": true}\nreasoning</think> Answer: {"ok": true} done') == {'ok': True}
    assert _json_object('```json\n{"ok": true}\n```') == {'ok': True}
    with pytest.raises(ValueError):
        _json_object('[1, 2]')


def test_cli_renders_record(tmp_path, monkeypatch, capsys):
    db = tmp_path / 'db.sqlite'
    verdict = CouncilVerdict(topic='CLI proposal', executive_verdict='Ship it', risk_matrix='Watch latency')
    with Database(db) as store:
        store.save(verdict, [SeatOpinion('architect', title='Architect', stance='SUPPORT', latency_ms=125)],
                   [DialecticTurn('architect', challenge_target='quant', challenge_point='Check cost')])
    monkeypatch.setenv('AI_COUNCIL_DB_PATH', str(db))
    assert main(['--history']) == 0
    output = capsys.readouterr().out
    assert 'Architect' in output and 'SUPPORT' in output and '125 ms' in output
    assert 'Dialectic turns' in output and 'Check cost' in output
    assert '## Executive verdict' in output and 'Ship it' in output and '## Risk matrix' in output


def test_cli_renders_legacy_record(capsys):
    from ai_council.cli import _render_record

    _render_record({'verdict': {'confidence_score': None, 'duration_s': '2.5'},
                    'opinions': [{}],
                    'turns': [{'seat_role': 'primary', 'role': 'ignored'},
                              {'role': 'legacy'}, {'title': 'Advisor'}, {},
                              {'seat_role': '', 'role': 'fallback'}]})
    output = capsys.readouterr().out
    for name in ('primary', 'legacy', 'Advisor', 'Specialist', 'fallback'):
        assert name in output
    assert 'Confidence 0/10 · 2.50s' in output
    _render_record({})
