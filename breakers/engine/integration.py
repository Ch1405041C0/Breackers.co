from __future__ import annotations

from typing import Any

from breakers.agents import build_core_agent_registry
from breakers.engine.evaluator import default_evaluator
from breakers.engine.loop import AgenticEngine
from breakers.engine.planner import default_planner


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


def context_from_scan_report(report: dict[str, Any]) -> dict[str, Any]:
    """Translate the existing SCAN contract into the Agentic Engine contract.

    This adapter keeps SCAN backwards compatible while allowing the new engine
    to reason over evidence already produced by Breakers.
    """
    return {
        "scan_source": report.get("source") or {},
        "scan_analyzers": list(report.get("analyzers") or []),
        "risks": _risk_values(report),
        "evidence": _evidence_values(report),
        "limitations": list((report.get("risk_summary") or {}).get("limitations") or []),
        "requested_scenarios": list(report.get("requested_scenarios") or []),
        "discovered_scenarios": list(report.get("discovered_scenarios") or []),
        "requirements": list(report.get("requirements") or []),
    }


def analyze_scan_report(report: dict[str, Any], max_cycles: int = 3) -> dict[str, Any]:
    engine = AgenticEngine(
        registry=build_core_agent_registry(),
        planner=default_planner,
        evaluator=default_evaluator,
    )
    state = engine.run(
        objective="Evaluate SCAN output for quality gaps, risk, coverage, and evidence.",
        context=context_from_scan_report(report),
        max_cycles=max_cycles,
    )
    return state.to_dict()
