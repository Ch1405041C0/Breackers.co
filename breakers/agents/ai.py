from __future__ import annotations

import json
from time import perf_counter
from typing import Any

from breakers.providers import ModelProvider, ModelRequest


SYSTEM_PROMPT = """You are the Breakers Quality Analyst.
First understand what the supplied evidence represents in its business, technical and operational context. Then evaluate quality using the supplied quality context and criteria.
Treat evidence-understanding profiles as hypotheses supported by matched signals, never as facts by themselves. Use quality criteria as evaluation targets, never as proof of compliance.
Never invent evidence. Distinguish observed facts, supported inferences, unknowns and hypotheses. Never claim ISO or other standards compliance from incomplete evidence.
Identify quality risks, evidence gaps and scenarios the requested scope may have missed. Recommend additional evidence or technical verification only when it is needed to evaluate a criterion.
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


def _quality_values(payload: dict[str, Any], finding_type: str) -> list[Any]:
    return _unique_values([
        item.get("value", item)
        for item in payload.get("findings") or []
        if item.get("type") == finding_type
    ])


def build_ai_risk_agent(provider: ModelProvider):
    """Create the AI quality/risk analyst while keeping the engine provider-agnostic."""

    def ai_risk_agent(payload: dict[str, Any]) -> dict[str, Any]:
        context = payload.get("context") or {}
        ai_context = {
            key: _unique_values(context.get(key))
            for key in (
                "requirements",
                "risks",
                "evidence",
                "evidence_fragments",
                "limitations",
                "requested_scenarios",
                "discovered_scenarios",
            )
        }
        ai_context["evidence_understanding"] = _quality_values(payload, "evidence_understanding")
        ai_context["quality_context"] = _quality_values(payload, "quality_context")
        ai_context["quality_criteria"] = _quality_values(payload, "quality_criterion")
        ai_context["quality_evidence_needs"] = _quality_values(payload, "quality_evidence_need")
        request = ModelRequest(
            task=(
                "Understand the supplied evidence and analyze this SCAN context for quality risks, "
                "evidence gaps and missed scenarios against the supplied quality criteria."
            ),
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
