"""Forecast recording and Brier calibration, optionally persisted in SQLite."""
from dataclasses import dataclass
import math
import sqlite3
import threading
from pathlib import Path


@dataclass
class BrierRecord:
    seat: str
    claim_id: str
    predicted_prob: float
    outcome: int | None
    correlation_id: str


class BrierEngine:
    def __init__(self, path=':memory:'):
        if str(path) != ':memory:':
            path = Path(path).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(path), timeout=30, check_same_thread=False)
        self._lock = threading.RLock()
        self.connection.execute('CREATE TABLE IF NOT EXISTS brier_forecasts (seat TEXT NOT NULL, claim_id TEXT NOT NULL, predicted_prob REAL NOT NULL, outcome INTEGER, correlation_id TEXT NOT NULL)')
        self.connection.commit()

    def record_forecast(self, seat: str, claim_id: str, prob: float, correlation_id: str):
        if not math.isfinite(prob) or not 0 <= prob <= 1:
            raise ValueError('probability must be between 0 and 1')
        with self._lock, self.connection:
            self.connection.execute('INSERT INTO brier_forecasts VALUES (?, ?, ?, NULL, ?)', (seat, claim_id, prob, correlation_id))

    def resolve_outcome(self, claim_id: str, outcome: int):
        if outcome not in (0, 1):
            raise ValueError('outcome must be 0 or 1')
        with self._lock, self.connection:
            self.connection.execute('UPDATE brier_forecasts SET outcome=? WHERE claim_id=?', (outcome, claim_id))

    def _stats(self, seat):
        with self._lock:
            return self.connection.execute('SELECT COUNT(*), AVG((predicted_prob-outcome)*(predicted_prob-outcome)) FROM brier_forecasts WHERE seat=? AND outcome IS NOT NULL', (seat,)).fetchone()

    def compute_brier_score(self, seat: str) -> float | None:
        return self._stats(seat)[1]

    def get_seat_weight(self, seat: str, beta: float = 2.0) -> float:
        count, score = self._stats(seat)
        return math.exp(-beta * score) if count >= 5 else 1.0

    def status(self):
        with self._lock:
            seats = [row[0] for row in self.connection.execute('SELECT DISTINCT seat FROM brier_forecasts ORDER BY seat')]
            return [{'seat': seat, 'resolved': self._stats(seat)[0], 'score': self.compute_brier_score(seat), 'weight': self.get_seat_weight(seat)} for seat in seats]

    def close(self):
        self.connection.close()
