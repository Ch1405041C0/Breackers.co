from __future__ import annotations

import json
from time import perf_counter
from typing import Any

from breakers.providers import ModelProvider, ModelRequest


SYSTEM_PROMPT = """You are the Breakers Risk Analyst.
Analyze only the supplied QA evidence. Identify quality risks, coverage gaps and scenarios the requested scope may have missed.
Never invent evidence. Distinguish observed facts from hypotheses.
Be concise. Return only JSON with keys findings, gaps and decisions. Each array item must be an object.
"""

AI_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {"type": "array", "items": {"type": "object"}},
        "gaps": {"type": "array", "items": {"type": "object"}},
        "decisions": {"type": "array", "items": {"type": "object"}},
    },
    "required": ["findings", "gaps", "decisions"],
    "additionalProperties": False,
}


def _unique_values(values: Any) -> list[Any]:
    if not isinstance(values, list):
        return []
    unique: dict[str, Any] = {}
    for value in values:
        key = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
        unique.setdefault(key, value)
    return list(unique.values())


def build_ai_risk_agent(provider: ModelProvider):
    """Create an AI risk agent while keeping the engine provider-agnostic."""

    def ai_risk_agent(payload: dict[str, Any]) -> dict[str, Any]:
        context = payload.get("context") or {}
        ai_context = {
            key: _unique_values(context.get(key))
            for key in (
                "requirements",
                "risks",
                "evidence",
                "limitations",
                "requested_scenarios",
                "discovered_scenarios",
            )
        }
        request = ModelRequest(
            task="Analyze this SCAN context for additional QA risks and coverage gaps.",
            system=SYSTEM_PROMPT,
            context=ai_context,
            response_schema=AI_RESPONSE_SCHEMA,
        )
        context_bytes = len(json.dumps(ai_context, ensure_ascii=False, default=str).encode("utf-8"))
        started = perf_counter()
        response = None
        call_metadata: dict[str, Any] = {}
        try:
            response = provider.generate(request)
            call_metadata = (response.raw or {}).get("_breakers_observability") or {}
            data = json.loads(response.content)
            if not isinstance(data, dict):
                raise ValueError("model response is not a JSON object")
            findings = data.get("findings")
            gaps = data.get("gaps")
            decisions = data.get("decisions")
            if not all(isinstance(value, list) for value in (findings, gaps, decisions)):
                raise ValueError("model response must contain findings, gaps and decisions arrays")
            if any(not isinstance(item, dict) for values in (findings, gaps, decisions) for item in values):
                raise ValueError("model response array items must be JSON objects")
            metadata = call_metadata
            decisions.append({
                "type": "ai_analysis_completed",
                "provider": response.provider,
                "model": response.model,
                "duration_ms": metadata.get("duration_ms", round((perf_counter() - started) * 1000)),
                "context_bytes": metadata.get("context_bytes", context_bytes),
                "payload_bytes": metadata.get("payload_bytes"),
                "thinking_enabled": metadata.get("thinking_enabled"),
                "prompt_eval_count": metadata.get("prompt_eval_count"),
                "eval_count": metadata.get("eval_count"),
                "prompt_tokens": metadata.get("prompt_tokens"),
                "completion_tokens": metadata.get("completion_tokens"),
                "total_tokens": metadata.get("total_tokens"),
                "ollama_total_duration_ms": metadata.get("ollama_total_duration_ms"),
            })
            return {"findings": findings, "gaps": gaps, "decisions": decisions}
        except Exception as exc:
            metadata = getattr(exc, "metadata", {}) or call_metadata
            try:
                provider_health = provider.health()
            except Exception:
                provider_health = {"ok": True}
            failed = provider_health.get("ok") is not False
            return {
                "findings": [],
                "gaps": [],
                "decisions": [{
                    "type": "ai_analysis_failed" if failed else "ai_analysis_unavailable",
                    "provider": provider.name,
                    "model": metadata.get(
                        "model",
                        response.model if response is not None else getattr(provider, "model", None),
                    ),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "duration_ms": metadata.get("duration_ms", round((perf_counter() - started) * 1000)),
                    "context_bytes": metadata.get("context_bytes", context_bytes),
                    "payload_bytes": metadata.get("payload_bytes"),
                    "thinking_enabled": metadata.get("thinking_enabled"),
                    "prompt_tokens": metadata.get("prompt_tokens"),
                    "completion_tokens": metadata.get("completion_tokens"),
                    "total_tokens": metadata.get("total_tokens"),
                }],
            }

    return ai_risk_agent
