from .models import Finding

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "UNKNOWN"}


def normalize_finding(engine: str, severity: str, title: str, evidence: str = "", category: str = "quality") -> Finding:
    normalized = str(severity or "UNKNOWN").upper()
    if normalized not in VALID_SEVERITIES:
        normalized = "UNKNOWN"
    return Finding(
        engine=str(engine or "BREAKERS"),
        severity=normalized,
        title=str(title or "Hallazgo"),
        evidence=str(evidence or ""),
        category=str(category or "quality"),
    )


def normalize_findings(findings) -> list[Finding]:
    result = []
    for item in findings:
        if isinstance(item, Finding):
            result.append(item)
        else:
            result.append(normalize_finding(**item))
    return result
