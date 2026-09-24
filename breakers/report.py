from collections import Counter

from .models import Finding
from .scoring import calculate_score


def build_report(target: str, engines: list[str], findings: list[Finding]) -> dict:
    scoring = calculate_score(findings)
    categories = Counter(f.category for f in findings)
    return {
        "target": target,
        "mode": "safe",
        "engines": engines,
        "findings": [f.to_dict() for f in findings[:200]],
        "summary": {
            **scoring,
            "by_category": dict(categories),
        },
        # Compatibility with the current frontend.
        "score": scoring["score"],
    }
