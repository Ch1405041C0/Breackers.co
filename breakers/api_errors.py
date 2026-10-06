from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ApiError:
    """Stable public error contract shared by Breakers API endpoints."""

    code: str
    message: str
    action: str | None = None
    trace_id: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.action:
            payload["action"] = self.action
        if self.trace_id:
            payload["trace_id"] = self.trace_id
        if self.details:
            payload["details"] = dict(self.details)
        return {"error": payload}


def api_error(
    code: str,
    message: str,
    *,
    action: str | None = None,
    trace_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return ApiError(
        code=code,
        message=message,
        action=action,
        trace_id=trace_id,
        details=details,
    ).to_dict()
