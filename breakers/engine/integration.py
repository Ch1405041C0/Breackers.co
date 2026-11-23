from __future__ import annotations

from pathlib import Path
import re
from time import perf_counter
from typing import Any

from breakers.agents import build_core_agent_registry
from breakers.agents.ai import build_ai_risk_agent
from breakers.engine.evaluator import default_evaluator
from breakers.engine.loop import AgenticEngine
from breakers.engine.planner import default_planner
from breakers.memory import JsonMemoryStore
from breakers.observability import log_scan_event
from breakers.providers import ModelProvider, build_model_provider

DEFAULT_MEMORY_PATH = Path(".breakers") / "memory.json"


def _safe_ai_error(value: Any) -> str | None:
    if value is None:
        return None
    message = str(value)[:500]
    if re.search(r"(?i)\b(token|password|secret|api[_-]?key)\b", message):
        return "Provider error details redacted because they may contain credentials."
    return re.sub(r"(https?://)[^/@\s]+:[^/@\s]+@", r"\1[REDACTED]@", message)


def _risk_values(report: dict[str, Any]) -> list[Any]:
    return list(report.get("risks") or [])


def _evidence_values(report: dict[str, Any]) -> list[Any]:
    evidence: list[Any] = []
    for finding in report.get("findings") or []:
        evidence.append(finding)
    source = report.get("source")
    if source:
        evidence.append({"type": "scan_source", "value": source})
    return evidence


def _memory_subject(report: dict[str, Any]) -> str:
    source = report.get("source") or {}
    return str(source.get("target") or source.get("commit_sha") or source.get("type") or "unknown")


def context_from_scan_report(
    report: dict[str, Any],
    memories: list[dict[str, Any]] | None = None,
    evidence_fragments: list[dict[str, Any]] | None = None,
    quality_hints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Translate SCAN output into the Agentic Engine context contract."""
    return {
        "scan_source": report.get("source") or {},
        "scan_analyzers": list(report.get("analyzers") or []),
        "risks": _risk_values(report),
        "evidence": _evidence_values(report),
        "evidence_fragments": list(evidence_fragments or []),
        "quality_hints": dict(quality_hints or {}),
        "limitations": list((report.get("risk_summary") or {}).get("limitations") or []),
        "requested_scenarios": list(report.get("requested_scenarios") or []),
        "discovered_scenarios": list(report.get("discovered_scenarios") or []),
        "requirements": list(report.get("requirements") or []),
        "memory": list(memories or []),
    }


def analyze_scan_report(
    report: dict[str, Any],
    max_cycles: int = 3,
    memory_store: JsonMemoryStore | None = None,
    model_provider: ModelProvider | None = None,
    job_id: str | None = None,
    evidence_fragments: list[dict[str, Any]] | None = None,
    quality_hints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    store = memory_store or JsonMemoryStore(DEFAULT_MEMORY_PATH)
    subject = _memory_subject(report)
    previous = store.recall("scan", subject=subject, limit=5)

    registry = build_core_agent_registry(include_quality=True)
    provider = model_provider or build_model_provider()
    ai_handler = build_ai_risk_agent(provider)

    def observed_ai_risk_agent(payload: dict[str, Any]) -> dict[str, Any]:
        started = perf_counter()
        cycle = payload.get("cycle")
        log_scan_event(
            "analyzer_started",
            job_id,
            name="IA",
            status="started",
            cycle=cycle,
            model=getattr(provider, "model", None),
        )
        try:
            result = ai_handler(payload)
        except Exception:
            log_scan_event(
                "analyzer_failed",
                job_id,
                name="IA",
                status="error",
                cycle=cycle,
                duration_ms=round((perf_counter() - started) * 1000),
                error="El análisis de IA produjo un error inesperado.",
            )
            raise
        agent_duration_ms = round((perf_counter() - started) * 1000)
        ai_decision = next(
            (
                decision for decision in reversed(result.get("decisions") or [])
                if decision.get("type") in {
                    "ai_analysis_completed",
                    "ai_analysis_unavailable",
                    "ai_analysis_failed",
                }
            ),
            {},
        )
        telemetry = {
            "model": ai_decision.get("model"),
            "provider": ai_decision.get("provider", provider.name),
            "duration_ms": ai_decision.get("duration_ms", agent_duration_ms),
            "agent_duration_ms": agent_duration_ms,
            "context_bytes": ai_decision.get("context_bytes"),
            "payload_bytes": ai_decision.get("payload_bytes"),
            "thinking_enabled": ai_decision.get("thinking_enabled"),
            "prompt_eval_count": ai_decision.get("prompt_eval_count"),
            "eval_count": ai_decision.get("eval_count"),
            "prompt_tokens": ai_decision.get("prompt_tokens"),
            "completion_tokens": ai_decision.get("completion_tokens"),
            "total_tokens": ai_decision.get("total_tokens"),
            "ollama_total_duration_ms": ai_decision.get("ollama_total_duration_ms"),
        }
        if ai_decision.get("type") == "ai_analysis_unavailable":
            log_scan_event(
                "analyzer_unavailable",
                job_id,
                name="IA",
                status="unavailable",
                cycle=cycle,
                **telemetry,
                error_type=ai_decision.get("error_type"),
                error=_safe_ai_error(ai_decision.get("error")),
            )
        elif ai_decision.get("type") == "ai_analysis_failed":
            log_scan_event(
                "analyzer_failed",
                job_id,
                name="IA",
                status="error",
                cycle=cycle,
                **telemetry,
                error_type=ai_decision.get("error_type"),
                error=_safe_ai_error(ai_decision.get("error")),
            )
        else:
            log_scan_event(
                "analyzer_completed",
                job_id,
                name="IA",
                status="executed",
                cycle=cycle,
                **telemetry,
            )
        return result

    registry.register(
        "ai_risk",
        "Uses the configured private or cloud model provider to refine semantic context and discover additional QA risks and coverage gaps.",
        observed_ai_risk_agent,
    )

    def logging_planner(state, agent_registry):
        planned = default_planner(state, agent_registry)
        if state.cycle > 1:
            planned = [agent for agent in planned if agent != "ai_risk"]
        log_scan_event(
            "agents_planned",
            job_id,
            cycle=state.cycle,
            agents=planned,
        )
        return planned

    engine = AgenticEngine(
        registry=registry,
        planner=logging_planner,
        evaluator=default_evaluator,
    )
    state = engine.run(
        objective="Understand supplied evidence, establish quality context and evaluate SCAN output for quality gaps, risk, coverage, and evidence.",
        context=context_from_scan_report(
            report,
            memories=previous,
            evidence_fragments=evidence_fragments,
            quality_hints=quality_hints,
        ),
        max_cycles=max_cycles,
    )
    result = state.to_dict()
    executed_agents = [
        item["agent"]
        for item in result["observations"]
        if item.get("kind") == "agent_completed"
    ]
    log_scan_event(
        "agents_executed",
        job_id,
        agents=executed_agents,
        total=len(executed_agents),
    )
    store.remember(
        "scan",
        subject,
        {
            "run_id": result["run_id"],
            "cycle": result["cycle"],
            "findings": result["findings"],
            "gaps": result["gaps"],
            "decisions": result["decisions"],
            "completed_reason": result["completed_reason"],
        },
    )
    result["memory"] = {
        "subject": subject,
        "recalled": len(previous),
        "persisted": True,
    }
    result["model_provider"] = {
        "name": provider.name,
        "health": provider.health(),
    }
    return result
