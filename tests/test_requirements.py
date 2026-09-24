from breakers.analyzers.requirements import analyze_requirements_text
from breakers.risk.engine import assess_risks


def test_detects_boundary_risk_from_functional_text():
    risks = analyze_requirements_text("El monto máximo permitido es 500000 pesos.")
    assert any(r.area == "business_rules" for r in risks)
    assert any("límite" in r.title.lower() for r in risks)


def test_detects_conditional_rule_without_inventing_bug():
    risks = analyze_requirements_text("Si el cliente está habilitado se confirma la operación.")
    assert risks
    risk = risks[0]
    assert risk.status == "identified"
    assert risk.missing_evidence
    assert "puede" in risk.hypothesis.lower()


def test_correlation_keeps_stable_risk_and_adds_evidence():
    risks = analyze_requirements_text("El monto máximo es 10.\nEl límite permitido es 10.")
    correlated = assess_risks(risks)
    boundary = [r for r in correlated if "límite" in r.title.lower()]
    assert len(boundary) == 1
    assert len(boundary[0].evidence) == 2
