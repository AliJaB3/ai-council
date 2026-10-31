"""In-process ordered deliberation events."""
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4


@dataclass(frozen=True)
class DeliberationEvent:
    seq: int
    event_id: str
    correlation_id: str
    timestamp: str
    event_type: str
    payload: dict


class DeliberationEventStream:
    def __init__(self, max_events: int = 1000):
        if max_events < 1:
            raise ValueError("max_events must be positive")
        self._history = deque(maxlen=max_events)
        self._sequence = 0
        self._listeners = []
        self._lock = RLock()

    def subscribe(self, listener_fn):
        with self._lock:
            self._listeners.append(listener_fn)

    def emit(self, event_type, correlation_id, payload):
        with self._lock:
            self._sequence += 1
            event = DeliberationEvent(self._sequence, str(uuid4()), correlation_id,
                                      datetime.now(timezone.utc).isoformat(), event_type, dict(payload))
            self._history.append(event)
            for listener in tuple(self._listeners):
                listener(event)
            return event

    def get_history(self, correlation_id=None):
        with self._lock:
            return [e for e in self._history if correlation_id is None or e.correlation_id == correlation_id]
