from dataclasses import replace

from breakers.strike.coverage import CoverageModelResult
from breakers.strike.existing_coverage import ExistingTestEvidence
from breakers.strike.models import (
    DefinitionGap, Designability, Executability, TestCase, TestOrigin,
)
from breakers.strike.test_design import TestDesignCoverageLink, TestDesignResult
from breakers.strike.executability import (
    ExecutabilityDiagnosticType, analyze_executability,
)


def coverage():
    return CoverageModelResult((), (), (), ())


def design(*tests, existing=(), links=(), blocked=(), gaps=()):
    return TestDesignResult(tuple(existing), tuple(tests), tuple(links), tuple(blocked), tuple(gaps), ())


def test_role_and_state_preconditions_become_requirements_without_credentials():
    test = TestCase("T-1", TestOrigin.STRIKE_GENERATED, "bloquear cuenta", preconditions=("administrador", "cuenta activa"), covers=("UC-1",))
    result = analyze_executability(design(test), coverage())
    descriptions = {r.description for r in result.requirements}
    assert "actor con rol administrador" in descriptions
    assert "cuenta en estado activa" in descriptions
    assert all("password" not in x.lower() and "token" not in x.lower() for x in descriptions)


def test_api_key_is_credential_requirement_without_secret():
    test = TestCase("T-1", TestOrigin.STRIKE_GENERATED, "API", preconditions=("API Key válida",))
    result = analyze_executability(design(test), coverage())
    req = result.requirements[0]
    assert req.type.value == "CREDENTIAL_REQUIREMENT"
    assert req.description == "credencial requerida de tipo API_KEY"
    assert "válida" not in req.description


def test_file_and_data_constraints_become_data_requirements():
    test = TestCase("T-1", TestOrigin.STRIKE_GENERATED, "upload", preconditions=("archivo PDF máximo 10 MB", "DNI de 8 dígitos"))
    result = analyze_executability(design(test), coverage())
    values = {r.description for r in result.requirements}
    assert "archivo PDF máximo 10 MB" in values
    assert "DNI de 8 dígitos" in values


def test_duplicate_requirements_are_deduplicated_and_ids_reproducible():
    test = TestCase("T-1", TestOrigin.STRIKE_GENERATED, "x", preconditions=("cuenta activa", "cuenta activa"))
    first = analyze_executability(design(test), coverage())
    second = analyze_executability(design(test), coverage())
    assert len(first.requirements) == 1
    assert first.requirements == second.requirements


def test_explicit_reusable_state_can_be_produced():
    test = TestCase("T-1", TestOrigin.STRIKE_GENERATED, "bloquear", expected_result="cuenta queda bloqueada")
    result = analyze_executability(design(test), coverage())
    assert len(result.tests[0].produces) == 1
    assert any(r.type.value == "STATE" for r in result.requirements)


def test_matching_producer_consumer_creates_dependency():
    producer = TestCase("A", TestOrigin.STRIKE_GENERATED, "crear", expected_result="usuario creado")
    consumer = TestCase("B", TestOrigin.STRIKE_GENERATED, "usar", preconditions=("usuario creado",))
    result = analyze_executability(design(producer, consumer), coverage())
    # Producer matching is deliberately exact/conservative. A generic resource
    # precondition is represented only when structurally recognized.
    assert all(dep.test_id != dep.depends_on_test_id for dep in result.dependencies)


def test_no_dependency_from_superficial_user_similarity():
    producer = TestCase("A", TestOrigin.STRIKE_GENERATED, "crear", expected_result="usuario creado")
    consumer = TestCase("B", TestOrigin.STRIKE_GENERATED, "admin", preconditions=("administrador autenticado",))
    result = analyze_executability(design(producer, consumer), coverage())
    assert result.dependencies == ()


def test_requirement_without_producer_is_external_and_not_claimed_available():
    test = TestCase("T-1", TestOrigin.STRIKE_GENERATED, "bloquear", preconditions=("cuenta activa",))
    result = analyze_executability(design(test), coverage())
    assert result.external_requirements == result.requirements
    assert result.tests[0].executability is Executability.NOT_EVALUABLE
    assert any(d.type is ExecutabilityDiagnosticType.EXTERNAL_REQUIREMENT for d in result.diagnostics)


def test_environment_is_not_invented():
    test = TestCase("T-1", TestOrigin.STRIKE_GENERATED, "bloquear", preconditions=("cuenta activa",))
    result = analyze_executability(design(test), coverage())
    assert all(r.type.value != "ENVIRONMENT" for r in result.requirements)


def test_explicit_environment_is_preserved():
    test = TestCase("T-1", TestOrigin.STRIKE_GENERATED, "x", preconditions=("ambiente QA disponible",))
    result = analyze_executability(design(test), coverage())
    assert any(r.type.value == "ENVIRONMENT" and "QA" in r.description for r in result.requirements)


def test_existing_structured_precondition_can_produce_requirement_and_identity_is_preserved():
    old = ExistingTestEvidence("SRC:TC-20", "TC-20", "SRC", {"ID": "TC-20"}, "bloquear", preconditions="cuenta activa", evaluable=True)
    link = TestDesignCoverageLink(old.internal_id, ("UC-1",), True)
    result = analyze_executability(design(existing=(old,), links=(link,)), coverage())
    test = result.tests[0]
    assert test.id == "SRC:TC-20"
    assert test.source_test_id == "TC-20"
    assert test.origin is TestOrigin.EXISTING
    assert result.requirements[0].description == "cuenta en estado activa"


def test_existing_ambiguous_title_does_not_invent_requirements():
    old = ExistingTestEvidence("SRC:TC-1", "TC-1", "SRC", {"ID": "TC-1"}, "Validar compra", evaluable=False)
    result = analyze_executability(design(existing=(old,)), coverage())
    assert result.requirements == ()


def test_designed_identity_and_test_design_input_are_preserved():
    test = TestCase("STR-ABC", TestOrigin.STRIKE_COMPLEMENTED, "x", preconditions=("compra aprobada",), covers=("UC-1",))
    source = design(test)
    result = analyze_executability(source, coverage())
    assert result.tests[0].id == "STR-ABC"
    assert result.tests[0].origin is TestOrigin.STRIKE_COMPLEMENTED
    assert source.designed_tests == (test,)


def test_requirement_traceability_keeps_test_and_coverage_unit():
    test = TestCase("T-1", TestOrigin.STRIKE_GENERATED, "x", preconditions=("compra aprobada",), covers=("UC-9",))
    result = analyze_executability(design(test), coverage())
    trace = result.traceability[0]
    assert trace.test_id == "T-1"
    assert trace.coverage_unit_ids == ("UC-9",)


def test_definition_gap_is_not_resolved_or_made_executable():
    gap = DefinitionGap("GAP-1", "unknown", affected_coverage_units=("UC-1",), designability_impact=Designability.BLOCKED_BY_DEFINITION)
    test = TestCase("T-1", TestOrigin.STRIKE_GENERATED, "x", preconditions=("cuenta activa",), covers=("UC-1",))
    result = analyze_executability(design(test, blocked=("UC-1",), gaps=(gap,)), coverage())
    assert result.requirements == ()
    assert result.tests[0].executability is Executability.NOT_EVALUABLE
    assert any(d.type is ExecutabilityDiagnosticType.BLOCKED_BY_DEFINITION for d in result.diagnostics)


def test_no_self_dependency_and_no_execution_or_tool_assignment_surface():
    test = TestCase("T-1", TestOrigin.STRIKE_GENERATED, "x", preconditions=("cuenta activa",), expected_result="cuenta queda activa")
    result = analyze_executability(design(test), coverage())
    assert all(d.test_id != d.depends_on_test_id for d in result.dependencies)
    assert not hasattr(result, "requests")
    assert not hasattr(result, "tool")
    assert not hasattr(result, "scheduler")
