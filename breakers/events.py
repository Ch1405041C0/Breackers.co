from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any


@dataclass(frozen=True)
class ScanEvent:
    name: str
    at: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "at": self.at, "data": dict(self.data)}


class ScanEventLedger:
    """Thread-safe in-memory event ledger for one SCAN execution."""

    def __init__(self) -> None:
        self._events: list[ScanEvent] = []
        self._lock = Lock()

    def record(self, name: str, **data: Any) -> ScanEvent:
        event = ScanEvent(
            name=name,
            at=datetime.now(timezone.utc).isoformat(),
            data=data,
        )
        with self._lock:
            self._events.append(event)
        return event

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [event.to_dict() for event in self._events]
