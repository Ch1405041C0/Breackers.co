from __future__ import annotations

from typing import Any


QUALITY_FRAMEWORKS = {
    "iso_iec_25010_2023": {
        "name": "ISO/IEC 25010:2023",
        "role": "product_quality_model",
    },
    "iso_iec_25012_2008": {
        "name": "ISO/IEC 25012:2008",
        "role": "data_quality_model",
    },
    "iso_iec_25020_2019": {
        "name": "ISO/IEC 25020:2019",
        "role": "quality_measurement_framework",
    },
    "iso_9001_2026": {
        "name": "ISO 9001:2026",
        "role": "quality_management_system",
    },
}


BASE_FOCUS = {
    "web": [
        "functional_suitability",
        "reliability",
        "security",
        "performance_efficiency",
        "accessibility",
    ],
    "repository": [
        "functional_suitability",
        "reliability",
        "security",
        "performance_efficiency",
        "maintainability",
    ],
    "api": [
        "functional_suitability",
        "reliability",
        "security",
        "performance_efficiency",
        "contract_quality",
    ],
    "app": [
        "functional_suitability",
        "reliability",
        "security",
        "performance_efficiency",
        "accessibility",
    ],
    "document": ["functional_suitability", "reliability", "security"],
    "image": ["interaction_quality", "accessibility"],
    "test_evidence": ["coverage", "traceability"],
}


CRITERION_LIBRARY = {
    "functional_suitability": {
        "statement": "Critical behavior must be explicit enough to verify expected outcomes, boundaries and exception paths.",
        "evidence_required": ["requirements", "acceptance_criteria", "observable_behavior"],
    },
    "reliability": {
        "statement": "Critical flows must define and evidence behavior for failure, retry, recovery and duplicate requests when applicable.",
        "evidence_required": ["failure_behavior", "recovery_behavior", "retry_or_idempotency_rules"],
    },
    "security": {
        "statement": "Sensitive capabilities and information must be protected by explicit controls and must not expose credentials or known critical weaknesses.",
        "evidence_required": ["access_controls", "secret_exposure_evidence", "vulnerability_evidence"],
    },
    "performance_efficiency": {
        "statement": "Critical operations must have measurable performance expectations appropriate to their usage context.",
        "evidence_required": ["performance_thresholds", "workload_context", "measurement_results"],
    },
    "maintainability": {
        "statement": "The implementation must provide measurable evidence about structural quality, dependencies and change risk.",
        "evidence_required": ["static_quality_evidence", "dependency_evidence", "change_risk_evidence"],
    },
    "accessibility": {
        "statement": "User-facing interactions must provide objective accessibility evidence for the rendered experience.",
        "evidence_required": ["rendered_ui", "accessibility_results"],
    },
    "contract_quality": {
        "statement": "API behavior must be represented by a coherent contract with explicit inputs, outputs, errors and constraints.",
        "evidence_required": ["api_contract", "error_contract", "schema_constraints"],
    },
    "interaction_quality": {
        "statement": "Visible states, labels, actions and feedback must be coherent and traceable to intended behavior.",
        "evidence_required": ["ui_state", "expected_interaction", "visual_evidence"],
    },
    "coverage": {
        "statement": "Available tests must be traceable to the behaviors and risks they claim to cover.",
        "evidence_required": ["test_cases", "requirements_or_risks", "coverage_links"],
    },
    "traceability": {
        "statement": "Quality conclusions must remain traceable from source evidence to criterion, finding and decision.",
        "evidence_required": ["source_references", "criterion_links", "decision_evidence"],
    },
    "data_quality": {
        "statement": "Critical structured data must have explicit, measurable rules for validity, completeness and consistency in its usage context.",
        "evidence_required": ["data_rules", "schema_or_profile", "data_quality_measurements"],
    },
    "integrity": {
        "statement": "State-changing critical operations must preserve business and data integrity across partial failure and retry scenarios.",
        "evidence_required": ["state_transition_rules", "failure_evidence", "integrity_checks"],
    },
    "process_quality": {
        "statement": "Quality-management claims must be supported by explicit process objectives, responsibilities, controls and improvement evidence.",
        "evidence_required": ["process_definition", "quality_objectives", "control_records", "improvement_evidence"],
    },
}


def _normalized_source(source: dict[str, Any]) -> tuple[str, str]:
    input_type = str(source.get("input_type") or "").strip().lower()
    subtype = str(source.get("subtype") or "").strip().lower()
    legacy_type = str(source.get("type") or "").strip().lower()

    if input_type:
        return input_type, subtype
    legacy = {
        "repository": ("repository", "repository"),
        "functional_document": ("file", "document"),
        "screen": ("file", "image"),
        "api_artifact": ("api", "api_contract"),
        "test_evidence": ("file", "test_evidence"),
    }
    return legacy.get(legacy_type, ("unknown", legacy_type or "unknown"))


def _truthy(hints: dict[str, Any], *keys: str) -> bool:
    return any(bool(hints.get(key)) for key in keys)


def _append_unique(values: list[str], *items: str) -> None:
    for item in items:
        if item and item not in values:
            values.append(item)


def build_quality_context(source: dict[str, Any], hints: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a grounded quality context before external engine selection.

    The contract deliberately separates observed input facts from inferred quality focus.
    It does not claim standards compliance and it records missing business context instead
    of inventing it.
    """
    hints = dict(hints or {})
    input_type, subtype = _normalized_source(source)

    observed = {
        "input_type": input_type,
        "subtype": subtype,
        "target": source.get("target"),
        "locator": source.get("locator"),
    }
    provided = {
        key: value
        for key, value in hints.items()
        if value not in (None, "", [], {}, ())
    }

    focus_key = subtype if input_type == "file" else input_type
    focus = list(BASE_FOCUS.get(focus_key, []))
    frameworks: list[dict[str, str]] = []

    software_like = input_type in {"web", "repository", "api", "app"} or subtype == "document"
    if software_like:
        frameworks.append({
            "id": "iso_iec_25010_2023",
            **QUALITY_FRAMEWORKS["iso_iec_25010_2023"],
            "reason": "The identified evidence concerns an ICT/software product or its requirements.",
        })
        frameworks.append({
            "id": "iso_iec_25020_2019",
            **QUALITY_FRAMEWORKS["iso_iec_25020_2019"],
            "reason": "BREAKERS requires objective, documented quality measurement rather than unsupported judgment.",
        })

    data_relevant = _truthy(
        hints,
        "data_quality_relevant",
        "structured_data",
        "data_store",
        "database",
        "analytics_data",
    )
    if data_relevant:
        frameworks.append({
            "id": "iso_iec_25012_2008",
            **QUALITY_FRAMEWORKS["iso_iec_25012_2008"],
            "reason": "The supplied context explicitly indicates structured-data quality is relevant.",
        })
        _append_unique(focus, "data_quality")

    sensitive = _truthy(
        hints,
        "handles_personal_data",
        "handles_financial_data",
        "sensitive_data",
        "regulated_data",
    )
    if sensitive:
        _append_unique(focus, "security", "integrity", "traceability")

    process_scope = _truthy(
        hints,
        "quality_management_scope",
        "organization_process_scope",
        "process_quality_relevant",
    )
    if process_scope:
        frameworks.append({
            "id": "iso_9001_2026",
            **QUALITY_FRAMEWORKS["iso_9001_2026"],
            "reason": "The supplied context explicitly places organizational quality-management processes in scope.",
        })
        _append_unique(focus, "process_quality")

    priorities = hints.get("quality_priorities") or []
    if isinstance(priorities, str):
        priorities = [priorities]
    if isinstance(priorities, list):
        for priority in priorities:
            value = str(priority).strip().lower()
            if value:
                _append_unique(focus, value)

    unknowns: list[str] = []
    if not hints.get("product_purpose"):
        unknowns.append("product_purpose")
    if not hints.get("criticality"):
        unknowns.append("criticality")
    if software_like and not any(
        key in hints for key in (
            "handles_personal_data",
            "handles_financial_data",
            "sensitive_data",
            "regulated_data",
            "data_quality_relevant",
            "structured_data",
        )
    ):
        unknowns.append("data_profile")

    confidence = "high" if len(unknowns) == 0 else "medium" if len(unknowns) == 1 else "low"
    return {
        "contract": "quality-context/v0.1",
        "observed": observed,
        "provided_context": provided,
        "frameworks": frameworks,
        "quality_focus": focus,
        "unknowns": unknowns,
        "confidence": confidence,
        "compliance_claimed": False,
    }


def build_quality_criteria(quality_context: dict[str, Any]) -> list[dict[str, Any]]:
    """Turn quality focus into explicit criteria and evidence needs.

    Criteria are BREAKERS evaluation criteria informed by the selected frameworks;
    they are not declarations of standards compliance.
    """
    framework_ids = [item.get("id") for item in quality_context.get("frameworks") or []]
    criteria: list[dict[str, Any]] = []
    for index, focus in enumerate(quality_context.get("quality_focus") or [], 1):
        template = CRITERION_LIBRARY.get(str(focus))
        if template is None:
            template = {
                "statement": f"The quality concern '{focus}' must be expressed as an observable and measurable criterion before a conclusion is made.",
                "evidence_required": ["explicit_criterion", "objective_evidence"],
            }
        relevant_frameworks = list(framework_ids)
        if focus == "data_quality":
            relevant_frameworks = [item for item in framework_ids if item == "iso_iec_25012_2008"] or relevant_frameworks
        elif focus == "process_quality":
            relevant_frameworks = [item for item in framework_ids if item == "iso_9001_2026"] or relevant_frameworks
        criteria.append({
            "id": f"QC-{index:03d}",
            "focus": focus,
            "statement": template["statement"],
            "evidence_required": list(template["evidence_required"]),
            "framework_refs": relevant_frameworks,
            "measurement_required": True,
            "status": "NEEDS_EVIDENCE",
        })
    return criteria
