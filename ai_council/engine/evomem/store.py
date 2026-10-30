"""Thread-safe SQLite memory provider."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
import sqlite3
import threading
from pathlib import Path
from ...contracts.memory_provider import MemoryProvider
from ...contracts.records import MemoryRecord, TrustState
from .validator import MemoryValidator

class EvoMemStore(MemoryProvider):
    def __init__(self, path, validator=None):
        if str(path) != ':memory:': Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY, tenant TEXT NOT NULL, state TEXT NOT NULL, data TEXT NOT NULL)')
        self.db.commit()
        self.validator = validator or MemoryValidator()
    def _write(self, record):
        self.db.execute('UPDATE memories SET state=?, data=? WHERE id=?', (record.trust_state, json.dumps(asdict(record)), record.id))
        self.db.commit()
    def _get(self, record_id):
        row = self.db.execute('SELECT data FROM memories WHERE id=?', (record_id,)).fetchone()
        if row is None: raise KeyError(record_id)
        return MemoryRecord(**json.loads(row[0]))
    @staticmethod
    def _expired(record):
        if not record.expires_at: return False
        try:
            t = datetime.fromisoformat(record.expires_at.replace('Z', '+00:00'))
            if t.tzinfo is None: return True
            return t <= datetime.now(timezone.utc)
        except (ValueError, TypeError): return True
    def propose(self, record):
        with self.lock:
            data = asdict(record); data['trust_state'] = TrustState.QUARANTINED
            record = MemoryRecord(**data)
            self.db.execute('INSERT INTO memories VALUES (?, ?, ?, ?)', (record.id, record.tenant_id, record.trust_state, json.dumps(asdict(record))))
            self.db.commit()
            return record.id
    def revalidate(self, record_id, is_valid):
        with self.lock:
            record = self._get(record_id)
            if record.trust_state in (TrustState.REVOKED, TrustState.EXPIRED): raise ValueError('terminal memory state')
            if self._expired(record): record.trust_state = TrustState.EXPIRED
            elif is_valid and self.validator.validate(record): record.trust_state = TrustState.VALIDATED
            else: record.trust_state = TrustState.QUARANTINED
            self._write(record)
            return record.trust_state
    def revoke(self, record_id):
        with self.lock:
            record = self._get(record_id); record.trust_state = TrustState.REVOKED; self._write(record)
    def _expire(self):
        for (data,) in self.db.execute("SELECT data FROM memories WHERE state IN ('QUARANTINED','VALIDATED')").fetchall():
            record = MemoryRecord(**json.loads(data))
            if self._expired(record): record.trust_state = TrustState.EXPIRED; self._write(record)
    def retrieve(self, query, limit, tenant_id):
        if limit <= 0: return []
        with self.lock:
            self._expire()
            rows = self.db.execute("SELECT data FROM memories WHERE tenant=? AND state='VALIDATED' ORDER BY rowid DESC", (tenant_id,)).fetchall()
            records = [MemoryRecord(**json.loads(row[0])) for row in rows]
            return [r for r in records if query.casefold() in json.dumps(r.payload, ensure_ascii=False).casefold()][:limit]
    def snapshot(self):
        with self.lock:
            self._expire()
            counts = {s.value: 0 for s in TrustState}
            counts.update(dict(self.db.execute('SELECT state, count(*) FROM memories GROUP BY state')))
            return counts
    def purge_revoked(self):
        with self.lock:
            cursor = self.db.execute("DELETE FROM memories WHERE state='REVOKED'"); self.db.commit(); return cursor.rowcount
    def close(self):
        with self.lock: self.db.close()
    def __enter__(self): return self
    def __exit__(self, *args): self.close()
