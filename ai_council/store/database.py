"""SQLite persistence, FTS search, and grounding invalidation."""
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from ..config import Settings
from ..engine.grounding import changed
from ..models import CouncilVerdict

class Database:
    def __init__(self, path=None):
        self.path = str(path or Settings().db_path)
        if self.path != ":memory:":
            Path(self.path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
            self.path = str(Path(self.path).expanduser())
        self.connection = sqlite3.connect(self.path, timeout=30)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self._migrate()
    def _migrate(self):
        # Namespaced tables avoid altering or destroying older council schemas.
        self.connection.executescript('''
        CREATE TABLE IF NOT EXISTS ccaa_decisions (id TEXT PRIMARY KEY, topic TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, verdict_json TEXT NOT NULL, opinions_json TEXT NOT NULL, turns_json TEXT NOT NULL, graph_json TEXT NOT NULL, grounding_json TEXT NOT NULL);
        CREATE VIRTUAL TABLE IF NOT EXISTS ccaa_decisions_fts USING fts5(id UNINDEXED, topic, content);
        CREATE TABLE IF NOT EXISTS ccaa_schema (version INTEGER NOT NULL);
        INSERT INTO ccaa_schema(version) SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM ccaa_schema);
        ''')
        self.connection.commit()
        self._import_legacy()
    def _import_legacy(self):
        """Import compatible rows from a legacy decisions table, preserving it."""
        tables = {r[0] for r in self.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'decisions' not in tables:
            return
        columns = {r[1] for r in self.connection.execute('PRAGMA table_info(decisions)')}
        if 'topic' not in columns:
            return
        for row in self.connection.execute('SELECT rowid AS _legacy_rowid, * FROM decisions').fetchall():
            data = dict(row)
            legacy_id = str(data.get('id') or 'legacy-' + str(data['_legacy_rowid']))
            if self.get(legacy_id):
                continue
            fields = CouncilVerdict.__dataclass_fields__
            values = {k: v for k, v in data.items() if k in fields and v is not None}
            values['id'] = legacy_id
            values['topic'] = str(data['topic'] or '')
            self.save(CouncilVerdict(**values))
    def save(self, verdict, opinions=None, turns=None, graph=None, grounding=None):
        encode = lambda value: json.dumps(value, ensure_ascii=False, default=lambda x: asdict(x))
        v = verdict.to_dict()
        ground = [{k: value for k, value in item.items() if k != "content"} for item in (grounding or [])]
        searchable = " ".join(str(v.get(k, "")) for k in ("executive_verdict", "emergent_architecture", "consensus_analysis", "implementation_blueprint", "risk_matrix", "kill_switch_criteria"))
        with self.connection:
            self.connection.execute("INSERT OR REPLACE INTO ccaa_decisions VALUES (?,?,?,?,?,?,?,?,?)", (verdict.id, verdict.topic, verdict.status, verdict.created_at, encode(v), encode(opinions or []), encode(turns or []), encode(graph or {}), encode(ground)))
            self.connection.execute("DELETE FROM ccaa_decisions_fts WHERE id=?", (verdict.id,))
            self.connection.execute("INSERT INTO ccaa_decisions_fts VALUES (?,?,?)", (verdict.id, verdict.topic, searchable))
    def get(self, decision_id):
        row = self.connection.execute("SELECT * FROM ccaa_decisions WHERE id=?", (decision_id,)).fetchone()
        return self._record(row) if row else None
    @staticmethod
    def _record(row):
        result = {k: json.loads(row[k + "_json"]) for k in ("verdict", "opinions", "turns", "graph", "grounding")}
        result["verdict"]["status"] = row["status"]
        return result
    def history(self, limit=100):
        return [self._record(row) for row in self.connection.execute("SELECT * FROM ccaa_decisions ORDER BY created_at DESC LIMIT ?", (limit,))]
    def search(self, term, limit=100):
        # Quote each token, preventing FTS operators from changing the query.
        tokens = term.split()
        if not tokens: return []
        query = " AND ".join('"' + token.replace('"', '""') + '"' for token in tokens)
        rows = self.connection.execute("SELECT d.* FROM ccaa_decisions_fts f JOIN ccaa_decisions d ON d.id=f.id WHERE ccaa_decisions_fts MATCH ? ORDER BY rank LIMIT ?", (query, limit))
        return [self._record(row) for row in rows]
    def check_stale(self):
        stale = []
        with self.connection:
            for row in self.connection.execute("SELECT id, grounding_json FROM ccaa_decisions WHERE status != 'STALE'").fetchall():
                if any(changed(item) for item in json.loads(row['grounding_json'])):
                    self.connection.execute("UPDATE ccaa_decisions SET status='STALE' WHERE id=?", (row['id'],))
                    stale.append(row['id'])
        return stale
    def close(self): self.connection.close()
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

CouncilStore = Database
