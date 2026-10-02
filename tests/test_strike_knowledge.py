from breakers.strike.knowledge import analyze_knowledge_gaps


def test_login_spec_surfaces_missing_quality_questions():
    findings = analyze_knowledge_gaps((
        "El usuario inicia sesión con usuario y contraseña. "
        "Después de 3 intentos fallidos la cuenta queda bloqueada. "
        "La sesión expira después de 30 minutos de inactividad.",
    ))
    questions = {item.question for item in findings}
    assert "¿Cómo y cuándo se desbloquea una cuenta bloqueada?" in questions
    assert any("múltiples sesiones simultáneas" in q for q in questions)
    assert any("longitud mínima/máxima" in q for q in questions)
    assert all(item.knowledge_ref for item in findings)


def test_defined_rule_is_not_reported_as_missing():
    findings = analyze_knowledge_gaps((
        "El usuario inicia sesión. La cuenta se desbloquea automáticamente después de 15 minutos.",
    ))
    assert not any("desbloquea una cuenta bloqueada" in item.question for item in findings)
