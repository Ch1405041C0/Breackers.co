from __future__ import annotations

from pathlib import Path
from typing import Any

from breakers.agents import build_core_agent_registry
from breakers.agents.ai import build_ai_risk_agent
from breakers.engine.evaluator import default_evaluator
from breakers.engine.loop import AgenticEngine
from breakers.engine.planner import default_planner
from breakers.memory import JsonMemoryStore
from breakers.providers import ModelProvider, build_model_provider

DEFAULT_MEMORY_PATH = Path(".breakers") / "memory.json"


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


def context_from_scan_report(report: dict[str, Any], memories: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Translate SCAN output into the Agentic Engine context contract."""
    return {
        "scan_source": report.get("source") or {},
        "scan_analyzers": list(report.get("analyzers") or []),
        "risks": _risk_values(report),
        "evidence": _evidence_values(report),
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
) -> dict[str, Any]:
    store = memory_store or JsonMemoryStore(DEFAULT_MEMORY_PATH)
    subject = _memory_subject(report)
    previous = store.recall("scan", subject=subject, limit=5)

    registry = build_core_agent_registry()
    provider = model_provider or build_model_provider()
    registry.register(
        "ai_risk",
        "Uses the configured private or cloud model provider to discover additional QA risks and coverage gaps.",
        build_ai_risk_agent(provider),
    )

    engine = AgenticEngine(
        registry=registry,
        planner=default_planner,
        evaluator=default_evaluator,
    )
    state = engine.run(
        objective="Evaluate SCAN output for quality gaps, risk, coverage, and evidence.",
        context=context_from_scan_report(report, memories=previous),
        max_cycles=max_cycles,
    )
    result = state.to_dict()
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
