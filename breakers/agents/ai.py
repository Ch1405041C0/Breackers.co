from __future__ import annotations

import json
from typing import Any

from breakers.providers import ModelProvider, ModelRequest


SYSTEM_PROMPT = """You are the Breakers Risk Analyst.
Analyze only the supplied QA evidence. Identify quality risks, coverage gaps and scenarios the requested scope may have missed.
Never invent evidence. Distinguish observed facts from hypotheses.
Return JSON with keys: findings, gaps, decisions. Each key must contain a JSON array.
"""


def build_ai_risk_agent(provider: ModelProvider):
    """Create an AI risk agent while keeping the engine provider-agnostic."""

    def ai_risk_agent(payload: dict[str, Any]) -> dict[str, Any]:
        context = payload.get("context") or {}
        request = ModelRequest(
            task="Analyze this SCAN context for additional QA risks and coverage gaps.",
            system=SYSTEM_PROMPT,
            context={
                "objective": payload.get("objective"),
                "cycle": payload.get("cycle"),
                "requirements": context.get("requirements") or [],
                "risks": context.get("risks") or [],
                "evidence": context.get("evidence") or [],
                "limitations": context.get("limitations") or [],
                "requested_scenarios": context.get("requested_scenarios") or [],
                "discovered_scenarios": context.get("discovered_scenarios") or [],
                "memory": context.get("memory") or [],
                "engine_findings": payload.get("findings") or [],
                "engine_gaps": payload.get("gaps") or [],
            },
        )
        try:
            response = provider.generate(request)
            data = json.loads(response.content)
            if not isinstance(data, dict):
                raise ValueError("model response is not a JSON object")
            findings = list(data.get("findings") or [])
            gaps = list(data.get("gaps") or [])
            decisions = list(data.get("decisions") or [])
            decisions.append({
                "type": "ai_analysis_completed",
                "provider": response.provider,
                "model": response.model,
            })
            return {"findings": findings, "gaps": gaps, "decisions": decisions}
        except Exception as exc:
            # AI is an enhancement, not a single point of failure. Deterministic
            # Breakers agents continue operating when the provider is unavailable.
            return {
                "findings": [],
                "gaps": [],
                "decisions": [{"type": "ai_analysis_unavailable", "provider": provider.name, "error": str(exc)}],
            }

    return ai_risk_agent
