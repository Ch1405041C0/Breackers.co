from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


@dataclass
class AgenticRunState:
    """Serializable state for one Breakers agentic analysis run."""

    objective: str
    context: dict[str, Any] = field(default_factory=dict)
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    cycle: int = 0
    max_cycles: int = 3
    status: str = "created"
    plan: list[str] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    gaps: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    completed_reason: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def next_cycle(self) -> int:
        self.cycle += 1
        self.status = "running"
        return self.cycle

    def record(self, kind: str, **payload: Any) -> None:
        self.observations.append({"kind": kind, "cycle": self.cycle, **payload})

    def finish(self, reason: str) -> None:
        self.status = "completed"
        self.completed_reason = reason

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "objective": self.objective,
            "context": self.context,
            "cycle": self.cycle,
            "max_cycles": self.max_cycles,
            "status": self.status,
            "plan": self.plan,
            "observations": self.observations,
            "findings": self.findings,
            "gaps": self.gaps,
            "decisions": self.decisions,
            "completed_reason": self.completed_reason,
            "created_at": self.created_at,
        }
