from __future__ import annotations

import json
import logging
from typing import Any


logger = logging.getLogger("app.scan")


def log_scan_event(event: str, job_id: str | None, **fields: Any) -> None:
    payload = {"event": event, **fields}
    if job_id:
        payload["job_id"] = job_id
    logger.info("%s", json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str))
