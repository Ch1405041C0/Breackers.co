from __future__ import annotations

from collections import Counter
from copy import deepcopy

EVIDENCE_STATES = {"preserved", "referenced_only", "source_not_retained"}


def _evidence_from_value(value: str) -> dict:
    value = str(value or "").strip()
    return {
        "summary": value,
        "availability": "source_not_retained" if value else "referenced_only",
    }


def _technical_finding(item: dict) -> dict:
    evidence = _evidence_from_value(item.get("evidence", ""))
    return {
        "title": str(item.get("title") or "Hallazgo"),
        "location": str(item.get("evidence") or ""),
        "evidence": [evidence],
        "risk": str(item.get("title") or "Hallazgo"),
        "priority": str(item.get("severity") or "UNKNOWN").upper(),
        "recommended_action": "",
        "area": str(item.get("category") or "quality"),
        "verification_status": "detected",
        "origin": "technical_finding",
    }


def _risk_finding(item: dict) -> dict:
    evidence = []
    for ev in item.get("evidence") or []:
        reference = str(ev.get("reference") or "")
        excerpt = str(ev.get("excerpt") or "")
        evidence.append({
            "summary": excerpt or reference,
            "reference": reference,
            "availability": "source_not_retained" if (reference or excerpt) else "referenced_only",
        })
    return {
        "title": str(item.get("title") or "Riesgo"),
        "location": evidence[0].get("reference", "") if evidence else "",
        "evidence": evidence,
        "risk": str(item.get("hypothesis") or item.get("title") or "Riesgo"),
        "priority": str(item.get("severity") or "UNKNOWN").upper(),
        "recommended_action": str(item.get("suggested_action") or ""),
        "area": str(item.get("area") or "quality"),
        "verification_status": str(item.get("status") or "identified"),
        "origin": "risk",
    }


def _coverage(report: dict) -> dict:
    required = list(report.get("required_engines") or [])
    performed = list(report.get("engines") or [])
    unavailable = list(report.get("unavailable_engines") or [])
    failed = list(report.get("failed_engines") or [])
    limitations = list((report.get("risk_summary") or {}).get("limitations") or [])
    limitations.extend(
        f"{item.get('engine', 'analysis')}: {item.get('error', 'failed')}" for item in failed
    )
    return {
        "intended_scope": ["quality and risk analysis"] if not required else [f"planned analysis: {name}" for name in required],
        "performed_coverage": [f"completed analysis: {name}" for name in performed],
        "unavailable_coverage": [f"unavailable analysis: {name}" for name in unavailable]
        + [f"failed analysis: {item.get('engine', 'analysis')}" for item in failed],
        "limitations": limitations,
    }


def build_scan_antecedent_snapshot(*, breakers_id: str, created_at: str, full_report: dict) -> dict:
    findings = [_technical_finding(item) for item in (full_report.get("findings") or [])]
    findings.extend(_risk_finding(item) for item in (full_report.get("risks") or []))
    severities = Counter(item["priority"] for item in findings)
    areas = Counter(item["area"] for item in findings)
    source = deepcopy(full_report.get("source") or {})
    source.pop("workspace", None)
    analyzed_state = source.get("commit_sha") or None
    coverage = _coverage(full_report)
    status = str(full_report.get("analysis_status") or "incomplete")
    score = full_report.get("score") if status == "completed" else None
    return {
        "identity": {
            "breakers_id": breakers_id,
            "product": "SCAN",
            "created_at": created_at,
            "analysis_status": status,
        },
        "analyzed": {
            "input_type": source.get("type"),
            "target_reference": full_report.get("target"),
            "source": source,
            "analyzed_state_reference": analyzed_state,
            "objective": full_report.get("objective"),
        },
        "coverage": coverage,
        "normalized_result": {
            "analysis_status": status,
            "score": score,
            "summary": deepcopy(full_report.get("summary") or {}),
            "risk_areas": dict(areas),
            "priority_distribution": dict(severities),
            "limitations": list(coverage["limitations"]),
        },
        "findings": findings,
        "evidence_policy": {
            "states": sorted(EVIDENCE_STATES),
            "source_artifacts_retained": False,
        },
        "deliverable": {
            "kind": "scan_full_report",
            "stored_separately": True,
        },
    }
