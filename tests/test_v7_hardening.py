import concurrent.futures
import os
import sqlite3
import time

import pytest

from ai_council.engine.mcp_client import MCPClient, MCPTool
from ai_council.engine.resilience import CircuitBreaker, IdempotencyManager
from ai_council.engine.sandbox_runner import sanitize_env
from ai_council.engine.streaming import DeliberationEventStream
from ai_council.store.database import Database, SingleWriterQueue, normalize_persian


def test_normalization_and_search(tmp_path):
    from ai_council.models import CouncilVerdict
    assert normalize_persian('كِتاب ي\u200cها') == 'کتاب ی ها'
    with Database(tmp_path / 'db') as db:
        db.save(CouncilVerdict(topic='كتاب'))
        assert db.search('کتاب')
        assert db.connection.execute('PRAGMA busy_timeout').fetchone()[0] == 5000


def test_writer_concurrent(tmp_path):
    conn = sqlite3.connect(tmp_path / 'queue.db', check_same_thread=False)
    conn.execute('create table entries (n integer)')
    writer = SingleWriterQueue()
    def insert(n):
        def write():
            with conn:
                conn.execute('insert into entries values (?)', (n,))
        writer.submit(write).result()
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(insert, range(100)))
    writer.close()
    assert conn.execute('select count(*) from entries').fetchone()[0] == 100
    conn.close()


def test_breaker_and_idempotency():
    breaker = CircuitBreaker(recovery_timeout=0.01)
    for _ in range(3): breaker.record_failure()
    assert not breaker.can_execute()
    time.sleep(0.02)
    assert breaker.can_execute() and breaker.state == breaker.HALF_OPEN
    assert not breaker.can_execute()
    breaker.record_success()
    assert breaker.state == breaker.CLOSED
    manager = IdempotencyManager()
    assert manager.register('key', 'hash')
    assert not manager.register('key', 'hash')
    manager.complete('key', {'ok': True})
    assert manager.get_cached('key') == {'ok': True}
    with pytest.raises(ValueError): manager.register('key', 'other')


def test_mcp_policy():
    client = MCPClient()
    assert not client.classify_tool('search_documents')
    assert client.classify_tool('delete_document')
    assert client.classify_tool('unknown')
    client._tools['delete_document'] = MCPTool('delete_document', '', {}, True)
    with pytest.raises(PermissionError): client.call_tool('delete_document')


def test_ring_and_env(monkeypatch):
    stream = DeliberationEventStream(max_events=2)
    for i in range(3): stream.emit('event', 'id', {'i': i})
    assert [event.seq for event in stream.get_history()] == [2, 3]
    monkeypatch.setenv('my_secret', 'hidden')
    assert 'my_secret' not in sanitize_env()


def test_mcp_stdio_round_trip(tmp_path):
    server = tmp_path / "server.py"
    server.write_text("""import json, sys
for line in sys.stdin:
    request = json.loads(line)
    if 'id' not in request: continue
    method = request['method']
    result = {'tools': [{'name': 'read_item', 'inputSchema': {}}, {'name': 'create_item', 'inputSchema': {}}]} if method == 'tools/list' else {'method': method}
    print(json.dumps({'jsonrpc': '2.0', 'id': request['id'], 'result': result}), flush=True)
""")
    import sys
    with MCPClient([sys.executable, str(server)]) as client:
        assert [tool.is_mutating for tool in client.list_tools()] == [False, True]
        assert client.call_tool('read_item')['method'] == 'tools/call'
        with pytest.raises(PermissionError): client.call_tool('create_item')
        assert client.call_tool('create_item', allow_mutating=True)['method'] == 'tools/call'
