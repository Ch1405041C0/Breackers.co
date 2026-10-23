from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import uuid


@dataclass
class MemoryRecord:
    namespace: str
    subject: str
    payload: dict[str, Any]
    record_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class JsonMemoryStore:
    """Small durable memory backend for Agentic Engine v1.

    JSON is intentionally the first backend: portable, inspectable and dependency-free.
    The engine contract can later be backed by SQLite/Postgres/vector storage without
    changing the agents that consume recalled memories.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        return data if isinstance(data, list) else []

    def _save(self, records: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def remember(self, namespace: str, subject: str, payload: dict[str, Any]) -> MemoryRecord:
        record = MemoryRecord(namespace=namespace, subject=subject, payload=payload)
        records = self._load()
        records.append(asdict(record))
        self._save(records)
        return record

    def recall(self, namespace: str, subject: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        records = [item for item in self._load() if item.get("namespace") == namespace]
        if subject is not None:
            records = [item for item in records if item.get("subject") == subject]
        return records[-max(0, limit):]
