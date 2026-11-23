from __future__ import annotations

from typing import Any


ENGINE_CATALOG = {
    "requirements": {
        "name": "BREAKERS Requirements Analyzer",
        "status": "integrated",
        "purpose": "ambiguity, conditions, boundaries and missing exception behavior",
        "execution_mode": "passive",
    },
    "trivy": {
        "name": "Trivy",
        "status": "integrated",
        "purpose": "vulnerabilities, misconfiguration and secrets",
        "execution_mode": "passive",
    },
    "gitleaks": {
        "name": "Gitleaks",
        "status": "integrated",
        "purpose": "secret detection",
        "execution_mode": "passive",
    },
    "sonar": {
        "name": "SonarQube / SonarScanner",
        "status": "detected_config_pending",
        "purpose": "static quality analysis",
        "execution_mode": "passive",
    },
    "zap": {
        "name": "OWASP ZAP",
        "status": "detected_config_pending",
        "purpose": "dynamic application security testing",
        "execution_mode": "active_authorized",
    },
    "jmeter": {
        "name": "JMeter",
        "status": "detected_config_pending",
        "purpose": "performance testing",
        "execution_mode": "active_authorized",
    },
    "spectral": {
        "name": "Spectral",
        "status": "next_integration",
        "purpose": "OpenAPI contract linting and custom rules",
        "execution_mode": "passive",
    },
    "schemathesis": {
        "name": "Schemathesis",
        "status": "next_integration",
        "purpose": "property-based API testing and edge cases",
        "execution_mode": "active_authorized",
    },
    "semgrep": {
        "name": "Semgrep",
        "status": "catalogued",
        "purpose": "static rules and risky patterns",
        "execution_mode": "passive",
    },
    "axe": {
        "name": "axe-core",
        "status": "catalogued",
        "purpose": "web accessibility",
        "execution_mode": "active_authorized",
    },
    "pa11y": {
        "name": "Pa11y",
        "status": "catalogued",
        "purpose": "automated web accessibility checks",
        "execution_mode": "active_authorized",
    },
    "k6": {
        "name": "k6",
        "status": "catalogued",
        "purpose": "load and performance testing",
        "execution_mode": "active_authorized",
    },
    "dependency_check": {
        "name": "OWASP Dependency-Check",
        "status": "catalogued",
        "purpose": "known vulnerable dependencies",
        "execution_mode": "passive",
    },
    "backstop": {
        "name": "BackstopJS",
        "status": "catalogued",
        "purpose": "visual regression",
        "execution_mode": "active_authorized",
    },
}


INTERNAL_ANALYZERS = {
    "repository": ["repository"],
    "api_contract": ["api_contract"],
    "document": ["requirements"],
    "image": ["ui_flow"],
    "test_evidence": ["coverage"],
}


def _engine(engine_id: str, reason: str) -> dict[str, Any]:
    return {"id": engine_id, **ENGINE_CATALOG[engine_id], "reason": reason, "will_execute": False}


def plan_scan_engines(source: dict[str, Any]) -> dict[str, Any]:
    """Return the engines that apply to an identified SCAN input without executing them."""
    input_type = str(source.get("input_type") or "").strip().lower()
    subtype = str(source.get("subtype") or "").strip().lower()
    locator = str(source.get("locator") or "").strip().lower()

    if input_type not in {"web", "repository", "api", "app", "file"}:
        raise ValueError(f"unsupported SCAN input_type for planning: {input_type or 'missing'}")

    analyzers: list[str] = []
    engines: list[dict[str, Any]] = []
    gaps: list[str] = []

    if input_type == "web":
        engines.extend([
            _engine("zap", "running website security surface"),
            _engine("axe", "rendered web accessibility"),
            _engine("pa11y", "rendered web accessibility"),
            _engine("backstop", "rendered UI visual regression"),
        ])
        gaps.append("web orchestration is not implemented yet")

    elif input_type == "repository":
        analyzers.extend(INTERNAL_ANALYZERS["repository"])
        engines.extend([
            _engine("trivy", "repository vulnerabilities and misconfiguration"),
            _engine("gitleaks", "repository secret detection"),
            _engine("sonar", "source-code quality analysis"),
            _engine("semgrep", "source-code risky pattern analysis"),
            _engine("dependency_check", "dependency vulnerability analysis"),
        ])

    elif input_type == "api":
        if subtype == "api_contract":
            analyzers.extend(INTERNAL_ANALYZERS["api_contract"])
            engines.extend([
                _engine("spectral", "OpenAPI or structured API contract"),
                _engine("schemathesis", "contract-derived API edge cases"),
            ])
        elif locator == "url":
            engines.extend([
                _engine("zap", "authorized running API security surface"),
                _engine("jmeter", "authorized running API performance"),
                _engine("k6", "authorized running API load and performance"),
            ])
        else:
            gaps.append("API reference needs a resolvable contract or authorized runtime URL")

    elif input_type == "app":
        gaps.append("mobile application engine is not defined in the BREAKERS engine catalog yet")

    elif input_type == "file":
        analyzers.extend(INTERNAL_ANALYZERS.get(subtype, []))
        if subtype == "document":
            engines.append(_engine("requirements", "functional or technical document"))
        elif subtype == "image":
            gaps.append("standalone image analyzer is registered but has no external engine mapped yet")
        elif subtype == "test_evidence":
            gaps.append("test evidence coverage analyzer is registered but has no external engine mapped yet")
        else:
            gaps.append(f"no engine matrix defined yet for file subtype: {subtype or 'unknown'}")

    return {
        "planning_status": "planned",
        "input_type": input_type,
        "subtype": subtype or None,
        "analyzers": analyzers,
        "engines": engines,
        "gaps": gaps,
        "execution_started": False,
    }
