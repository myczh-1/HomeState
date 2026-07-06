"""Facts Layer — raw event buffer."""

from __future__ import annotations

from collections import deque
from datetime import datetime

from .models import FactEvent


class FactsStore:
    """Ring buffer for raw HA events."""

    def __init__(self, limit: int = 5000) -> None:
        self._events: deque[FactEvent] = deque(maxlen=limit)

    def record(self, event: FactEvent) -> None:
        self._events.append(event)

    def latest(self, entity_id: str) -> FactEvent | None:
        for event in reversed(self._events):
            if event.entity_id == entity_id:
                return event
        return None

    def recent(self, entity_id: str, n: int = 10) -> list[FactEvent]:
        result = []
        for event in reversed(self._events):
            if event.entity_id == entity_id:
                result.append(event)
                if len(result) >= n:
                    break
        return list(reversed(result))

    def all_since(self, since: datetime) -> list[FactEvent]:
        return [e for e in self._events if e.timestamp > since]

    @property
    def count(self) -> int:
        return len(self._events)
