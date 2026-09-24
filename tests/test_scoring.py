from breakers.normalizer import normalize_finding
from breakers.scoring import calculate_score


def test_score_penalizes_by_severity():
    findings = [
        normalize_finding("Trivy", "CRITICAL", "A"),
        normalize_finding("Gitleaks", "HIGH", "B"),
        normalize_finding("Trivy", "LOW", "C"),
    ]
    result = calculate_score(findings)
    assert result["penalty"] == 17
    assert result["score"] == 83
    assert result["total_findings"] == 3


def test_unknown_severity_is_normalized():
    finding = normalize_finding("X", "banana", "Unexpected severity")
    assert finding.severity == "UNKNOWN"
