from __future__ import annotations

import json
from typing import Any

from breakers.engine.registry import AgentRegistry
from breakers.evidence_understanding import understand_evidence
from breakers.quality import build_quality_context, build_quality_criteria


def _context(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("context") or {}


def _stable(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def _previous_payloads(context: dict[str, Any]) -> list[dict[str, Any]]:
    return [item.get("payload") or {} for item in context.get("memory") or []]


def _previous_values(context: dict[str, Any], key: str, finding_type: str | None = None) -> list[Any]:
    values: list[Any] = []
    for memory in _previous_payloads(context):
        for item in memory.get(key) or []:
            if finding_type is None or item.get("type") == finding_type:
                values.append(item.get("value", item))
    return values


def _finding_values(payload: dict[str, Any], finding_type: str) -> list[Any]:
    return [
        item.get("value", item)
        for item in payload.get("findings") or []
        if item.get("type") == finding_type
    ]


def evidence_understanding_agent(payload: dict[str, Any]) -> dict[str, Any]:
    understanding = understand_evidence(_context(payload))
    return {
        "findings": [{"type": "evidence_understanding", "value": understanding}],
        "decisions": [{
            "type": "evidence_understanding_completed",
            "profiles": [item.get("id") for item in understanding.get("inferred_profiles") or []],
            "semantic_types": list(understanding.get("semantic_evidence_types") or []),
            "unknowns": list(understanding.get("unknowns") or []),
        }],
    }


def quality_context_agent(payload: dict[str, Any]) -> dict[str, Any]:
    context = _context(payload)
    source = context.get("scan_source") or context.get("source") or {}
    hints = dict(context.get("quality_hints") or {})

    understandings = _finding_values(payload, "evidence_understanding")
    evidence_understanding = understandings[-1] if understandings else {}
    inferred_focus = list(evidence_understanding.get("quality_focus_hints") or [])
    existing_priorities = hints.get("quality_priorities") or []
    if isinstance(existing_priorities, str):
        existing_priorities = [existing_priorities]
    hints["quality_priorities"] = list(dict.fromkeys([*existing_priorities, *inferred_focus]))
    hints["evidence_profiles"] = [
        {
            "id": item.get("id"),
            "confidence": item.get("confidence"),
            "status": item.get("status", "INFERRED"),
        }
        for item in evidence_understanding.get("inferred_profiles") or []
    ]
    hints["semantic_evidence_types"] = list(evidence_understanding.get("semantic_evidence_types") or [])

    quality_context = build_quality_context(source, hints)
    quality_context["evidence_understanding_contract"] = evidence_understanding.get("contract")
    quality_context["inferred_profiles"] = list(evidence_understanding.get("inferred_profiles") or [])

    findings = [{"type": "quality_context", "value": quality_context}]
    findings.extend(
        {
            "type": "quality_context_unknown",
            "value": field,
            "blocking": False,
        }
        for field in quality_context.get("unknowns") or []
    )
    return {
        "findings": findings,
        "decisions": [{
            "type": "quality_context_established",
            "confidence": quality_context.get("confidence"),
            "frameworks": [item.get("id") for item in quality_context.get("frameworks") or []],
            "compliance_claimed": False,
        }],
    }


def quality_criteria_agent(payload: dict[str, Any]) -> dict[str, Any]:
    contexts = _finding_values(payload, "quality_context")
    if not contexts:
        return {
            "findings": [],
            "decisions": [{"type": "quality_criteria_skipped", "reason": "quality_context_missing"}],
        }
    criteria = build_quality_criteria(contexts[-1])
    findings: list[dict[str, Any]] = []
    for criterion in criteria:
        findings.append({"type": "quality_criterion", "value": criterion})
        findings.append({
            "type": "quality_evidence_need",
            "value": {
                "criterion_id": criterion["id"],
                "focus": criterion["focus"],
                "evidence_required": list(criterion["evidence_required"]),
            },
        })
    return {
        "findings": findings,
        "decisions": [{
            "type": "quality_criteria_established",
            "count": len(criteria),
            "measurement_required": True,
        }],
    }


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

    previous = _previous_values(context, "findings", "risk")
    current_map = {_stable(item): item for item in risks}
    previous_map = {_stable(item): item for item in previous}
    recurring = [current_map[key] for key in sorted(current_map.keys() & previous_map.keys())]
    new = [current_map[key] for key in sorted(current_map.keys() - previous_map.keys())]
    resolved = [previous_map[key] for key in sorted(previous_map.keys() - current_map.keys())]

    if risks:
        decisions.append({"type": "risk_review_required", "count": len(risks)})
    if previous:
        decisions.append({
            "type": "risk_delta",
            "recurring": len(recurring),
            "new": len(new),
            "resolved": len(resolved),
        })
        findings.extend({"type": "recurring_risk", "value": item} for item in recurring)
        findings.extend({"type": "new_risk", "value": item} for item in new)
        findings.extend({"type": "resolved_risk", "value": item} for item in resolved)
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

    previous_uncovered = set(_previous_values(context, "findings", "scenario_outside_requested_scope"))
    if previous_uncovered:
        current_uncovered = set(uncovered)
        decisions.append({
            "type": "coverage_delta",
            "persistent": len(current_uncovered & previous_uncovered),
            "new": len(current_uncovered - previous_uncovered),
            "resolved": len(previous_uncovered - current_uncovered),
        })
    return {"findings": findings, "decisions": decisions}


def evidence_agent(payload: dict[str, Any]) -> dict[str, Any]:
    context = _context(payload)
    evidence = context.get("evidence") or []
    findings = [{"type": "evidence", "value": item} for item in evidence]
    gaps = [] if evidence else [{"type": "missing_evidence", "message": "No supporting evidence was supplied."}]

    previous_missing = any(
        item.get("type") == "missing_evidence"
        for memory in _previous_payloads(context)
        for item in memory.get("gaps") or []
    )
    decisions = []
    if previous_missing and evidence:
        decisions.append({"type": "evidence_gap_resolved"})
    elif previous_missing and not evidence:
        decisions.append({"type": "evidence_gap_persists"})
    return {"findings": findings, "gaps": gaps, "decisions": decisions}


def build_quality_agent_registry() -> AgentRegistry:
    registry = AgentRegistry()
    registry.register(
        "evidence_understanding",
        "Classifies what the supplied evidence means using grounded QA context profiles without turning inference into fact.",
        evidence_understanding_agent,
    )
    registry.register(
        "quality_context",
        "Establishes grounded product context, applicable quality frameworks and unknowns without claiming compliance.",
        quality_context_agent,
    )
    registry.register(
        "quality_criteria",
        "Turns the quality context into explicit measurable BREAKERS criteria and evidence needs.",
        quality_criteria_agent,
    )
    return registry


def build_core_agent_registry(*, include_quality: bool = False) -> AgentRegistry:
    registry = AgentRegistry()
    if include_quality:
        registry.register(
            "evidence_understanding",
            "Classifies what the supplied evidence means using grounded QA context profiles without turning inference into fact.",
            evidence_understanding_agent,
        )
        registry.register(
            "quality_context",
            "Establishes grounded product context, applicable quality frameworks and unknowns without claiming compliance.",
            quality_context_agent,
        )
        registry.register(
            "quality_criteria",
            "Turns the quality context into explicit measurable BREAKERS criteria and evidence needs.",
            quality_criteria_agent,
        )
    registry.register("requirements", "Identifies explicit requirements and missing requirement context.", requirements_agent)
    registry.register("risk", "Surfaces known product and quality risks and compares them with previous runs.", risk_agent)
    registry.register("coverage", "Contrasts requested scope, discovered scenarios, and historical coverage gaps.", coverage_agent)
    registry.register("evidence", "Checks whether conclusions are backed by evidence and tracks evidence gaps over time.", evidence_agent)
    return registry
