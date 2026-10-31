import time
import asyncio
import httpx
import pytest

from ai_council.config import Settings
from ai_council.models import CouncilVerdict
from ai_council.store.database import Database
from ai_council.web import server


@pytest.fixture
def client(tmp_path, monkeypatch):
    import anyio.to_thread
    async def run_sync(func, *args, **kwargs):
        return func(*args)
    monkeypatch.setattr(anyio.to_thread, "run_sync", run_sync)
    settings = Settings(db_path=str(tmp_path / 'council.sqlite'))
    app = server.create_app(settings)
    class Client:
        def __init__(self):
            self.app = app
        def request(self, method, url, **kwargs):
            async def run():
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as session:
                    return await session.request(method, url, **kwargs)
            return asyncio.run(run())
        def get(self, url, **kwargs):
            return self.request('GET', url, **kwargs)
        def post(self, url, **kwargs):
            return self.request('POST', url, **kwargs)
    return Client()


def test_dashboard_routes_and_seats(client):
    response = client.get('/')
    assert response.status_code == 200
    assert 'تالار زنده شورا' in response.text
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert client.get('/api/v1/runs').json() == []
    seats = client.get('/api/v1/seats/status').json()
    assert len(seats) == 6
    assert {s['role'] for s in seats} >= {'architect', 'arbiter'}
    assert client.get('/api/v1/runs/missing/snapshot').status_code == 404
    assert client.get('/api/v1/runs/missing/stream').status_code == 404


def test_search_and_snapshot(client):
    with Database(client.app.state.settings.db_path) as store:
        store.save(CouncilVerdict(id='decision', topic='كتاب فارسی', executive_verdict='A decision'))
    results = client.get('/api/v1/search', params={'q': 'کتاب'}).json()
    assert results[0]['run_id'] == 'decision'
    assert client.get('/api/v1/runs/decision/snapshot').json()['verdict']['executive_verdict'] == 'A decision'
    assert client.get('/api/v1/search', params={'q': '" OR *'}).status_code == 200


def test_background_convene_and_stream(client, monkeypatch):
    class FakeCouncil:
        def __init__(self, settings, store, event_stream):
            self.store, self.stream = store, event_stream
        def deliberate(self, topic, deep=False, fast_path=False):
            self.stream.emit('SEAT_COMMITTED', 'correlation', {'seat': 'architect'})
            verdict = CouncilVerdict(topic=topic, executive_verdict='Done')
            self.store.save(verdict)
            return verdict
    monkeypatch.setattr(server, 'CouncilOrchestrator', FakeCouncil)
    response = client.post('/api/v1/convene', json={'topic': 'Test', 'deep': True})
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'PENDING'
    run_id = data['run_id']
    for _ in range(200):
        snap = client.get(f'/api/v1/runs/{run_id}/snapshot').json()
        if snap['status'] == 'COMPLETE':
            break
        time.sleep(.01)
    assert snap['verdict']['executive_verdict'] == 'Done'
    stream = client.get(f'/api/v1/runs/{run_id}/stream')
    assert 'event: SEAT_COMMITTED' in stream.text
    assert 'event: RUN_COMPLETED' in stream.text
    resumed = client.get(f'/api/v1/runs/{run_id}/stream', headers={'Last-Event-ID': '2'})
    assert 'event: RUN_STARTED' not in resumed.text
    assert client.post('/api/v1/convene', json={'topic': '   '}).status_code == 422


def test_workshop_memory_and_cli(client, monkeypatch):
    assert client.get('/api/v1/workshop/ideas').json() == []
    result = client.post('/api/v1/workshop/run', json={'topic': 'software', 'count': 1})
    assert result.status_code == 200 and result.json()
    assert client.get('/api/v1/workshop/ideas').json()
    assert client.get('/api/v1/evomem/status').json()['counts']['QUARANTINED'] == 0
    assert client.post('/api/v1/evomem/missing/promote').status_code == 404
    from ai_council.cli import main
    import uvicorn
    calls = []
    monkeypatch.setattr(uvicorn, 'run', lambda *a, **kw: calls.append((a, kw)))
    assert main(['serve', '--port', '9000']) == 0
    assert calls[0][1] == {'host': '0.0.0.0', 'port': 9000}
