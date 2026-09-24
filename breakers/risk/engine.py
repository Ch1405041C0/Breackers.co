import hashlib
from .model import Evidence, Risk

SEVERITY_ORDER = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

def risk_id(area: str, title: str) -> str:
    fingerprint = hashlib.sha1(f"{area}|{title}".lower().encode()).hexdigest()[:8].upper()
    return f"RISK-{fingerprint}"

def make_risk(*, area: str, severity: str, title: str, hypothesis: str, source_type: str, reference: str, excerpt: str = "", confidence: float = 0.5, missing_evidence=None, suggested_action: str = "") -> Risk:
    severity = severity.upper()
    if severity not in SEVERITY_ORDER: severity = "MEDIUM"
    return Risk(id=risk_id(area, title), area=area, severity=severity, title=title, hypothesis=hypothesis, confidence=max(0.0, min(1.0, confidence)), evidence=[Evidence(source_type, reference, excerpt)], missing_evidence=list(missing_evidence or []), suggested_action=suggested_action)

def correlate(risks: list[Risk]) -> list[Risk]:
    grouped = {}
    for risk in risks:
        key = (risk.area.lower().strip(), risk.title.lower().strip())
        current = grouped.get(key)
        if current is None:
            grouped[key] = risk; continue
        current.evidence.extend(risk.evidence)
        current.missing_evidence = sorted(set(current.missing_evidence + risk.missing_evidence))
        current.confidence = min(0.99, current.confidence + 0.10)
        if SEVERITY_ORDER[risk.severity] > SEVERITY_ORDER[current.severity]: current.severity = risk.severity
    return list(grouped.values())

def assess_risks(candidate_risks: list[Risk]) -> list[Risk]:
    valid = [r for r in candidate_risks if r.evidence or r.missing_evidence]
    return correlate(valid)
