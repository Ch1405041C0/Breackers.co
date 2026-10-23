from __future__ import annotations

from typing import Any

from breakers.engine.registry import AgentRegistry


def _context(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("context") or {}


def requirements_agent(payload: dict[str, Any]) -> dict[str, Any]:
    context = _context(payload)
    requirements = context.get("requirements") or []
    findings = [{"type": "requirement", "value": item} for item in requirements]
    gaps = [] if requirements else [{"type": "missing_requirements", "message": "No explicit requirements were supplied."}]
    return {"findings": findings, "gaps": gaps}


def risk_agent(payload: dict[str, Any]) -> dict[str, Any]:
    context = _context(payload)
    risks = context.get("risks") or []
    findings = [{"type": "risk", "value": item} for item in risks]
    decisions = []
    if risks:
        decisions.append({"type": "risk_review_required", "count": len(risks)})
    return {"findings": findings, "decisions": decisions}


def coverage_agent(payload: dict[str, Any]) -> dict[str, Any]:
    context = _context(payload)
    requested = set(context.get("requested_scenarios") or [])
    discovered = set(context.get("discovered_scenarios") or [])
    uncovered = sorted(discovered - requested)
    findings = [{"type": "scenario_outside_requested_scope", "value": item} for item in uncovered]
    decisions = []
    if uncovered:
        decisions.append({
            "type": "scope_gap_detected",
            "requested": len(requested),
            "discovered": len(discovered),
            "outside_scope": len(uncovered),
        })
    return {"findings": findings, "decisions": decisions}


def evidence_agent(payload: dict[str, Any]) -> dict[str, Any]:
    context = _context(payload)
    evidence = context.get("evidence") or []
    findings = [{"type": "evidence", "value": item} for item in evidence]
    gaps = [] if evidence else [{"type": "missing_evidence", "message": "No supporting evidence was supplied."}]
    return {"findings": findings, "gaps": gaps}


def build_core_agent_registry() -> AgentRegistry:
    registry = AgentRegistry()
    registry.register("requirements", "Identifies explicit requirements and missing requirement context.", requirements_agent)
    registry.register("risk", "Surfaces known product and quality risks.", risk_agent)
    registry.register("coverage", "Contrasts requested scope with scenarios Breakers discovers.", coverage_agent)
    registry.register("evidence", "Checks whether conclusions are backed by evidence.", evidence_agent)
    return registry
