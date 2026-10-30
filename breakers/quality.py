from __future__ import annotations

from typing import Any


QUALITY_FRAMEWORKS = {
    "iso_iec_25010_2023": {
        "name": "ISO/IEC 25010:2023",
        "role": "product_quality_model",
    },
    "iso_iec_25012": {
        "name": "ISO/IEC 25012",
        "role": "data_quality_model",
    },
    "iso_iec_25020": {
        "name": "ISO/IEC 25020",
        "role": "quality_measurement_framework",
    },
    "iso_9001": {
        "name": "ISO 9001",
        "role": "quality_management_system",
    },
}


# These are conservative technical baselines. File contents do not receive a
# product-quality focus merely because they are a document or image.
BASE_FOCUS = {
    "web": [
        "functional_suitability",
        "reliability",
        "security",
        "performance_efficiency",
        "accessibility",
    ],
    "repository": [
        "security",
        "maintainability",
        "traceability",
    ],
    "api": [
        "functional_suitability",
        "reliability",
        "security",
        "contract_quality",
    ],
    "app": [
        "functional_suitability",
        "reliability",
        "security",
        "performance_efficiency",
        "usability",
        "accessibility",
        "compatibility",
    ],
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
        "statement": "Sensitive capabilities and information must be protected by explicit controls and objective security evidence.",
        "evidence_required": ["assets_or_data_sensitivity", "access_controls", "security_verification_evidence"],
    },
    "performance_efficiency": {
        "statement": "Critical operations must have measurable performance expectations tied to business, operational and workload context.",
        "evidence_required": ["performance_objectives", "workload_or_operational_profile", "measurement_results"],
    },
    "maintainability": {
        "statement": "The implementation must provide evidence about structural quality, dependencies and change risk appropriate to the product context.",
        "evidence_required": ["static_quality_evidence", "dependency_evidence", "change_risk_evidence"],
    },
    "accessibility": {
        "statement": "User-facing interactions must have explicit accessibility goals and objective evidence against the applicable user context.",
        "evidence_required": ["user_context", "accessibility_criteria", "accessibility_results"],
    },
    "usability": {
        "statement": "Usability goals must be defined from the intended users, tasks and context of use and evaluated with suitable evidence.",
        "evidence_required": ["users", "tasks", "context_of_use", "usability_evidence"],
    },
    "compatibility": {
        "statement": "The relevant platforms, devices, environments and coexistence/interoperability conditions must be explicit and verifiable.",
        "evidence_required": ["supported_platforms", "environment_matrix", "compatibility_results"],
    },
    "contract_quality": {
        "statement": "API behavior must be represented by a coherent contract with explicit inputs, outputs, errors and constraints.",
        "evidence_required": ["api_contract", "error_contract", "schema_constraints"],
    },
    "interaction_quality": {
        "statement": "Visible states, labels, actions and feedback must be coherent and traceable to intended behavior and users.",
        "evidence_required": ["ui_state", "expected_interaction", "visual_or_user_evidence"],
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
        "statement": "Critical data must have explicit, measurable rules for validity, completeness, consistency and fitness for its intended use.",
        "evidence_required": ["data_rules", "schema_or_profile", "data_quality_measurements"],
    },
    "integrity": {
        "statement": "State-changing critical operations must preserve business and data integrity across partial failure and retry scenarios.",
        "evidence_required": ["state_transition_rules", "failure_evidence", "integrity_checks"],
    },
    "measurement": {
        "statement": "Quality claims must be linked to obtainable measures, thresholds or observable decision rules appropriate to the objective.",
        "evidence_required": ["quality_objective", "measure_or_metric", "threshold_or_decision_rule"],
    },
    "explainability": {
        "statement": "Where AI decisions affect stakeholders, explainability expectations must identify the audience and an objective way to evaluate the explanation.",
        "evidence_required": ["stakeholder_profile", "explainability_goal", "evaluation_evidence"],
    },
    "bias": {
        "statement": "Where inappropriate bias is a product risk, relevant populations, data distributions and bias acceptance criteria must be explicit.",
        "evidence_required": ["population_or_slice_definition", "dataset_profile", "bias_measurement_or_review"],
    },
    "safety": {
        "statement": "Safety-relevant behavior must define unacceptable outcomes, operating boundaries and evidence that risk controls are effective.",
        "evidence_required": ["hazard_or_unacceptable_outcome", "operating_boundary", "safety_control_evidence"],
    },
    "localization_quality": {
        "statement": "Localization must be evaluated against the intended locale, cultural/linguistic rules and product-specific presentation constraints.",
        "evidence_required": ["target_locale", "localized_content", "locale_specific_criteria"],
    },
    "risk_based_testing": {
        "statement": "Test depth and priority must be traceable to identified product risks and their business or technical impact.",
        "evidence_required": ["product_risks", "risk_priority", "test_response"],
    },
    "compliance_evidence": {
        "statement": "Regulatory or standards-related obligations must be identified by jurisdiction/scope and supported by traceable verification evidence.",
        "evidence_required": ["applicable_obligation", "scope_or_jurisdiction", "verification_evidence"],
    },
    "process_quality": {
        "statement": "Quality-management claims must be supported by explicit process objectives, responsibilities, controls and improvement evidence.",
        "evidence_required": ["process_definition", "quality_objectives", "control_records", "improvement_evidence"],
    },
}


SOFTWARE_SEMANTIC_TYPES = {
    "requirements",
    "acceptance_criteria",
    "business_rules",
    "performance_requirements",
    "security_requirements",
    "usability_requirements",
    "accessibility_requirements",
    "mobile_application",
    "ai_system",
    "ml_model",
    "automation_strategy",
    "delivery_pipeline",
    "test_model",
    "agile_work_item",
    "regulated_domain_rules",
    "game_design",
    "game_mechanics",
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


def _add_framework(frameworks: list[dict[str, str]], framework_id: str, reason: str) -> None:
    if any(item.get("id") == framework_id for item in frameworks):
        return
    frameworks.append({"id": framework_id, **QUALITY_FRAMEWORKS[framework_id], "reason": reason})


def build_quality_context(source: dict[str, Any], hints: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a grounded quality context before external engine selection.

    Technical type is observed. Semantic profiles and quality priorities are inferred or
    explicitly supplied and remain distinguishable from facts. A generic file/document
    is never assumed to be software requirements solely from its extension.
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

    semantic_types = {
        str(value).strip().lower()
        for value in (hints.get("semantic_evidence_types") or [])
        if str(value).strip()
    }
    focus_key = subtype if input_type == "file" else input_type
    focus = list(BASE_FOCUS.get(focus_key, []))

    priorities = hints.get("quality_priorities") or []
    if isinstance(priorities, str):
        priorities = [priorities]
    if isinstance(priorities, list):
        for priority in priorities:
            value = str(priority).strip().lower()
            if value:
                _append_unique(focus, value)

    frameworks: list[dict[str, str]] = []
    software_like = input_type in {"web", "repository", "api", "app"} or bool(
        semantic_types & SOFTWARE_SEMANTIC_TYPES
    )
    if software_like:
        _add_framework(
            frameworks,
            "iso_iec_25010_2023",
            "Observed or semantically inferred evidence concerns an ICT/software product or its quality requirements.",
        )
        _add_framework(
            frameworks,
            "iso_iec_25020",
            "BREAKERS requires objective, documented measurement or observable decision rules for quality conclusions.",
        )

    data_relevant = _truthy(
        hints,
        "data_quality_relevant",
        "structured_data",
        "data_store",
        "database",
        "analytics_data",
    ) or "data_quality" in focus or bool({"dataset", "data_quality_rules"} & semantic_types)
    if data_relevant:
        _add_framework(
            frameworks,
            "iso_iec_25012",
            "The supplied or inferred context indicates data quality is relevant to the product decision.",
        )
        _append_unique(focus, "data_quality")

    sensitive = _truthy(
        hints,
        "handles_personal_data",
        "handles_financial_data",
        "sensitive_data",
        "regulated_data",
    ) or "sensitive_assets" in semantic_types
    if sensitive:
        _append_unique(focus, "security", "integrity", "traceability")

    process_scope = _truthy(
        hints,
        "quality_management_scope",
        "organization_process_scope",
        "process_quality_relevant",
    )
    if process_scope:
        _add_framework(
            frameworks,
            "iso_9001",
            "Organizational quality-management processes are explicitly in scope.",
        )
        _append_unique(focus, "process_quality")

    unknowns: list[str] = []
    profiles = hints.get("evidence_profiles") or []
    if input_type == "file" and subtype in {"document", "image", "generic_file", ""} and not profiles:
        unknowns.append("semantic_context")
    if software_like and not hints.get("product_purpose"):
        unknowns.append("product_purpose")
    if software_like and not hints.get("criticality"):
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
    ) and "data_quality" not in focus:
        unknowns.append("data_profile")

    confidence = "high" if len(unknowns) == 0 else "medium" if len(unknowns) == 1 else "low"
    return {
        "contract": "quality-context/v0.2",
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
            relevant_frameworks = [item for item in framework_ids if item == "iso_iec_25012"] or relevant_frameworks
        elif focus == "process_quality":
            relevant_frameworks = [item for item in framework_ids if item == "iso_9001"] or relevant_frameworks
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
