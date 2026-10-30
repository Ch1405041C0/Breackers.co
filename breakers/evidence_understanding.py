from __future__ import annotations

import re
import unicodedata
from typing import Any


KNOWLEDGE_PROFILES: dict[str, dict[str, Any]] = {
    "requirements_acceptance": {
        "knowledge_basis": "ISTQB Acceptance Testing",
        "signals": [
            "requirement", "requisito", "user story", "historia de usuario",
            "acceptance criteria", "criterio de aceptacion", "business rule", "regla de negocio",
            "given", "when", "then",
        ],
        "evidence_types": ["requirements", "acceptance_criteria", "business_rules"],
        "quality_focus": ["functional_suitability", "traceability", "coverage"],
    },
    "performance": {
        "knowledge_basis": "ISTQB Performance Testing",
        "signals": [
            "response time", "tiempo de respuesta", "throughput", "capacidad de procesamiento",
            "concurrent", "concurrencia", "load profile", "perfil de carga", "operational profile",
            "perfil operativo", "resource utilization", "utilizacion de recursos", "latency", "latencia",
        ],
        "evidence_types": ["performance_requirements", "workload_profile", "performance_metrics"],
        "quality_focus": ["performance_efficiency", "reliability", "measurement"],
    },
    "mobile": {
        "knowledge_basis": "ISTQB Mobile Application Testing",
        "signals": [
            "android", "ios", "mobile", "movil", "apk", "ipa", "screen orientation",
            "orientacion", "permission", "permiso", "sensor", "connectivity", "conectividad",
            "battery", "bateria", "app store", "tienda de aplicaciones", "device", "dispositivo",
        ],
        "evidence_types": ["mobile_application", "device_context", "mobile_runtime_conditions"],
        "quality_focus": ["compatibility", "usability", "security", "performance_efficiency", "reliability"],
    },
    "security": {
        "knowledge_basis": "ISTQB Security Test Engineer",
        "signals": [
            "authentication", "autenticacion", "authorization", "autorizacion", "encryption", "cifrado",
            "sensitive", "sensible", "security policy", "politica de seguridad", "privilege", "privilegio",
            "zero trust", "confianza cero", "vulnerability", "vulnerabilidad", "owasp", "pci dss",
        ],
        "evidence_types": ["security_requirements", "security_controls", "sensitive_assets"],
        "quality_focus": ["security", "integrity", "traceability"],
    },
    "usability_accessibility": {
        "knowledge_basis": "ISTQB Usability Testing",
        "signals": [
            "usability", "usabilidad", "user experience", "experiencia de usuario", "accessibility",
            "accesibilidad", "wcag", "heuristic", "heuristica", "user survey", "encuesta de usuario",
        ],
        "evidence_types": ["usability_requirements", "user_context", "accessibility_requirements"],
        "quality_focus": ["usability", "accessibility", "interaction_quality"],
    },
    "ai_ml": {
        "knowledge_basis": "ISTQB AI Testing",
        "signals": [
            "machine learning", "aprendizaje automatico", "model", "modelo", "dataset", "training data",
            "datos de entrenamiento", "bias", "sesgo", "explainability", "explicabilidad", "concept drift",
            "deriva", "non-deterministic", "no determinista", "ground truth", "test oracle", "oraculo",
        ],
        "evidence_types": ["ai_system", "ml_model", "dataset", "ai_acceptance_criteria"],
        "quality_focus": ["data_quality", "functional_suitability", "reliability", "explainability", "bias", "safety"],
    },
    "devops": {
        "knowledge_basis": "ISTQB Quality in DevOps",
        "signals": [
            "ci/cd", "pipeline", "continuous integration", "integracion continua", "continuous delivery",
            "continuous deployment", "deployment", "release", "devops", "dora", "monitoring", "observability",
            "observabilidad", "pull request",
        ],
        "evidence_types": ["delivery_pipeline", "quality_gate", "operational_evidence", "traceability_evidence"],
        "quality_focus": ["traceability", "reliability", "maintainability", "process_quality", "measurement"],
    },
    "test_automation": {
        "knowledge_basis": "ISTQB Test Automation Strategy",
        "signals": [
            "test automation", "automatizacion de pruebas", "automation framework", "marco de automatizacion",
            "test script", "script de prueba", "roi", "return on investment", "retorno de inversion",
            "test data", "datos de prueba", "test environment", "entorno de prueba",
        ],
        "evidence_types": ["automation_strategy", "automation_assets", "test_environment", "test_data_dependency"],
        "quality_focus": ["maintainability", "traceability", "coverage", "measurement"],
    },
    "model_based_testing": {
        "knowledge_basis": "ISTQB Model-Based Testing",
        "signals": [
            "model-based testing", "model based testing", "mbt", "test model", "modelo de prueba",
            "state transition", "transicion de estados", "test selection criteria", "criterios de seleccion",
        ],
        "evidence_types": ["test_model", "model_requirements_links", "test_selection_criteria"],
        "quality_focus": ["coverage", "traceability", "functional_suitability"],
    },
    "agile": {
        "knowledge_basis": "ISTQB Agile Tester",
        "signals": [
            "sprint", "iteration", "iteracion", "backlog", "definition of done", "historia de usuario",
            "user story", "acceptance criteria", "criterios de aceptacion", "exploratory testing",
            "prueba exploratoria", "shift left",
        ],
        "evidence_types": ["agile_work_item", "iteration_scope", "definition_of_done", "test_charter"],
        "quality_focus": ["coverage", "traceability", "risk_based_testing"],
    },
    "gambling": {
        "knowledge_basis": "ISTQB Gambling Industry Tester",
        "signals": [
            "gambling", "wager", "wagering", "casino", "lottery", "lottery", "rng",
            "random number generator", "jackpot", "jurisdiction", "geolocation", "player privacy",
        ],
        "evidence_types": ["regulated_domain_rules", "gambling_logic", "jurisdictional_requirements"],
        "quality_focus": ["functional_suitability", "security", "integrity", "compliance_evidence", "reliability"],
    },
    "game": {
        "knowledge_basis": "ISTQB Game Testing",
        "signals": [
            "gameplay", "game mechanics", "mecanicas de juego", "game controller", "controlador",
            "graphics", "graficos", "sound", "audio", "multiplayer", "multiplatform", "localization",
            "localizacion", "player",
        ],
        "evidence_types": ["game_design", "game_mechanics", "game_runtime", "game_content"],
        "quality_focus": ["functional_suitability", "usability", "compatibility", "performance_efficiency", "localization_quality"],
    },
}


def _normalize(value: Any) -> str:
    text = str(value or "").lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).strip()


def _evidence_text(context: dict[str, Any]) -> str:
    chunks: list[str] = []
    for fragment in context.get("evidence_fragments") or []:
        if isinstance(fragment, dict):
            chunks.append(str(fragment.get("text") or fragment.get("value") or ""))
        else:
            chunks.append(str(fragment))
    for requirement in context.get("requirements") or []:
        chunks.append(str(requirement))
    for item in context.get("evidence") or []:
        if isinstance(item, dict):
            chunks.append(str(item.get("excerpt") or item.get("value") or item.get("title") or ""))
        else:
            chunks.append(str(item))
    return _normalize("\n".join(chunks))


def _technical_evidence_types(source: dict[str, Any]) -> list[str]:
    input_type = _normalize(source.get("input_type"))
    subtype = _normalize(source.get("subtype"))
    legacy_type = _normalize(source.get("type"))

    if input_type == "repository" or legacy_type == "repository":
        return ["source_code_repository"]
    if input_type == "api" or legacy_type == "api_artifact":
        return ["api_contract" if subtype == "api_contract" or legacy_type == "api_artifact" else "api_reference"]
    if input_type == "app":
        return ["mobile_application_artifact"]
    if subtype == "document" or legacy_type == "functional_document":
        return ["document"]
    if subtype == "image" or legacy_type == "screen":
        return ["visual_evidence"]
    if subtype == "test_evidence" or legacy_type == "test_evidence":
        return ["test_evidence"]
    if input_type == "web":
        return ["running_web_surface"]
    return ["unclassified_artifact"]


def understand_evidence(context: dict[str, Any]) -> dict[str, Any]:
    """Classify what the supplied evidence means before quality reasoning.

    This layer is intentionally conservative. Profile matches are hypotheses grounded in
    content signals, not declarations about the product. The AI analyst may refine them,
    but downstream logic can always distinguish observed facts from inferred profiles.
    """
    source = context.get("scan_source") or context.get("source") or {}
    text = _evidence_text(context)
    technical_types = _technical_evidence_types(source)

    profiles: list[dict[str, Any]] = []
    semantic_types: list[str] = []
    quality_focus: list[str] = []

    for profile_id, profile in KNOWLEDGE_PROFILES.items():
        matched = [signal for signal in profile["signals"] if _normalize(signal) in text]
        if not matched:
            continue
        confidence = "high" if len(matched) >= 4 else "medium" if len(matched) >= 2 else "low"
        profiles.append({
            "id": profile_id,
            "knowledge_basis": profile["knowledge_basis"],
            "matched_signals": matched[:8],
            "confidence": confidence,
            "status": "INFERRED",
        })
        for evidence_type in profile["evidence_types"]:
            if evidence_type not in semantic_types:
                semantic_types.append(evidence_type)
        for focus in profile["quality_focus"]:
            if focus not in quality_focus:
                quality_focus.append(focus)

    observed = {
        "technical_evidence_types": technical_types,
        "fragment_count": len(context.get("evidence_fragments") or []),
        "has_requirements": bool(context.get("requirements")),
        "has_scanner_evidence": bool(context.get("evidence")),
    }

    unknowns: list[str] = []
    if not profiles:
        unknowns.append("semantic_context")
    if "document" in technical_types and not semantic_types:
        unknowns.append("document_role")
    if "source_code_repository" in technical_types and not context.get("evidence_fragments"):
        unknowns.append("repository_purpose")

    return {
        "contract": "evidence-understanding/v0.1",
        "observed": observed,
        "inferred_profiles": profiles,
        "semantic_evidence_types": semantic_types,
        "quality_focus_hints": quality_focus,
        "unknowns": unknowns,
        "policy": {
            "profile_matches_are_evidence": False,
            "inferences_require_validation": True,
            "missing_context_is_reported": True,
        },
    }
