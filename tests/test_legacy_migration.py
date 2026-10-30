import json
import sqlite3
from ai_council.models import CouncilVerdict
from ai_council.store import Database


def test_council_decisions_migration_preserves_records_and_search(tmp_path):
    path = tmp_path / 'legacy.sqlite'
    with Database(path) as store:
        store.save(CouncilVerdict(id='existing', topic='Current', executive_verdict='current content'))
        store.connection.execute('CREATE TABLE council_decisions AS SELECT * FROM ccaa_decisions WHERE 0')
        verdict = CouncilVerdict(id='old', topic='Legacy topic', executive_verdict='distinctive archive')
        legacy = (verdict.id, verdict.topic, 'STALE', verdict.created_at, json.dumps(verdict.to_dict()),
                  '[{"role":"reviewer"}]', '[{"text":"turn"}]', '{"edges":[1]}', '[{"path":"source"}]')
        store.connection.execute('INSERT INTO council_decisions VALUES (?,?,?,?,?,?,?,?,?)', legacy)
        store.connection.execute('INSERT INTO council_decisions VALUES (?,?,?,?,?,?,?,?,?)',
                                 ('existing', 'Older', 'COMPLETE', verdict.created_at, json.dumps(verdict.to_dict()), '[]', '[]', '{}', '[]'))
        store.connection.commit()

    for _ in range(2):
        with Database(path) as store:
            record = store.get('old')
            assert record['verdict']['status'] == 'STALE'
            assert record['opinions'] == [{'role': 'reviewer'}]
            assert record['turns'] == [{'text': 'turn'}]
            assert record['graph'] == {'edges': [1]}
            assert record['grounding'] == [{'path': 'source'}]
            assert [r['verdict']['id'] for r in store.search('distinctive')] == ['old']
            assert store.get('existing')['verdict']['topic'] == 'Current'
            assert len(store.history()) == 2
            assert store.connection.execute('SELECT count(*) FROM council_decisions').fetchone()[0] == 2
            assert store.connection.execute("SELECT count(*) FROM ccaa_decisions_fts WHERE id='old'").fetchone()[0] == 1


def test_full_verdict_legacy_migration(tmp_path):
    path = tmp_path / 'legacy.sqlite'
    with sqlite3.connect(path) as connection:
        connection.execute('''CREATE TABLE council_decisions (
            id TEXT PRIMARY KEY, topic TEXT, status TEXT, created_at TEXT,
            full_verdict TEXT, confidence_score REAL, specialists_json TEXT,
            rebuttals_json TEXT, file_grounding_path TEXT)''')
        connection.execute('INSERT INTO council_decisions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                           ('old', 'Legacy topic', 'active', '2026-01-01', 'distinctive verdict',
                            8.5, '[{"role":"reviewer"}]', '[{"text":"turn"}]', '/source'))
        connection.execute('INSERT INTO council_decisions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                           ('empty', 'Other', 'active', '2026-01-02', 'other',
                            None, '[]', None, None))

    for _ in range(2):
        with Database(path) as store:
            record = store.get('old')
            assert record['verdict']['executive_verdict'] == 'distinctive verdict'
            assert record['verdict']['confidence_score'] == 8.5
            assert record['opinions'] == [{'role': 'reviewer'}]
            assert record['turns'] == [{'text': 'turn'}]
            assert record['grounding'] == [{'path': '/source'}]
            assert store.get('empty')['turns'] == []
            assert store.get('empty')['grounding'] == []
            assert len(store.history()) == 2
            assert len(store.search('distinctive')) == 1
