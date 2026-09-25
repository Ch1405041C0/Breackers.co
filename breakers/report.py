from collections import Counter

from .models import Finding
from .scoring import calculate_score


def build_report(
    target: str,
    engines: list[str],
    findings: list[Finding],
    *,
    required_engines: list[str] | None = None,
    unavailable_engines: list[str] | None = None,
    failed_engines: list[dict] | None = None,
) -> dict:
    required_engines = list(required_engines or [])
    unavailable_engines = list(unavailable_engines or [])
    failed_engines = list(failed_engines or [])

    missing_count = len(unavailable_engines) + len(failed_engines)
    if required_engines and not engines:
        analysis_status = "incomplete"
    elif missing_count:
        analysis_status = "partial"
    else:
        analysis_status = "completed"

    coverage_complete = analysis_status == "completed"
    scoring = calculate_score(findings, coverage_complete=coverage_complete)
    categories = Counter(f.category for f in findings)
    return {
        "target": target,
        "mode": "safe",
        "analysis_status": analysis_status,
        "required_engines": required_engines,
        "engines": engines,
        "unavailable_engines": unavailable_engines,
        "failed_engines": failed_engines,
        "findings": [f.to_dict() for f in findings[:200]],
        "summary": {
            **scoring,
            "coverage_complete": coverage_complete,
            "by_category": dict(categories),
        },
        # Compatibility with the current frontend: null means the planned coverage was incomplete.
        "score": scoring["score"],
    }
