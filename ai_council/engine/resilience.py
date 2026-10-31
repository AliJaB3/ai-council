"""Thread-safe resilience primitives for external operations."""
import threading
import time


class CircuitBreaker:
    CLOSED = 'CLOSED'
    OPEN = 'OPEN'
    HALF_OPEN = 'HALF_OPEN'

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 10.0):
        if failure_threshold < 1 or recovery_timeout < 0:
            raise ValueError('invalid circuit breaker configuration')
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = self.CLOSED
        self.failures = 0
        self._opened_at = None
        self._probe = False
        self._lock = threading.Lock()

    def can_execute(self) -> bool:
        with self._lock:
            if self.state == self.OPEN:
                if time.monotonic() - self._opened_at < self.recovery_timeout:
                    return False
                self.state = self.HALF_OPEN
            if self.state == self.HALF_OPEN:
                if self._probe:
                    return False
                self._probe = True
            return True

    def record_success(self):
        with self._lock:
            self.state = self.CLOSED
            self.failures = 0
            self._probe = False
            self._opened_at = None

    def record_failure(self):
        with self._lock:
            self.failures += 1
            if self.state == self.HALF_OPEN or self.failures >= self.failure_threshold:
                self.state = self.OPEN
                self._opened_at = time.monotonic()
            self._probe = False


class IdempotencyManager:
    def __init__(self):
        self._entries = {}
        self._lock = threading.Lock()

    def register(self, idempotency_key: str, payload_hash: str) -> bool:
        with self._lock:
            if idempotency_key in self._entries:
                if self._entries[idempotency_key][0] != payload_hash:
                    raise ValueError('idempotency key reused with a different payload')
                return False
            self._entries[idempotency_key] = (payload_hash, None)
            return True

    def complete(self, idempotency_key: str, result: dict):
        with self._lock:
            payload_hash, _ = self._entries[idempotency_key]
            self._entries[idempotency_key] = (payload_hash, dict(result))

    def get_cached(self, idempotency_key: str) -> dict | None:
        with self._lock:
            entry = self._entries.get(idempotency_key)
            return dict(entry[1]) if entry and entry[1] is not None else None
