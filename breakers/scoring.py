from collections import Counter

from .models import Finding

WEIGHTS = {"CRITICAL": 10, "HIGH": 6, "MEDIUM": 3, "LOW": 1, "INFO": 0, "UNKNOWN": 1}


def calculate_score(findings: list[Finding], coverage_complete: bool = True) -> dict:
    penalty = sum(WEIGHTS.get(f.severity, 1) for f in findings)
    score = max(0, 100 - min(100, penalty)) if coverage_complete else None
    severities = Counter(f.severity for f in findings)
    return {
        "score": score,
        "penalty": penalty,
        "total_findings": len(findings),
        "by_severity": dict(severities),
    }
