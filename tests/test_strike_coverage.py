import pytest

from breakers.strike.coverage import CoverageDiagnosticType, build_coverage_model
from breakers.strike.ingestion import SourceLocation
from breakers.strike.interpretation import (
    Contradiction,
    InterpretationCertainty,
    InterpretationResult,
    InterpretationType,
    interpreted_item,
)
from breakers.strike.models import (
    Designability,
    ExistingCoverage,
    Importance,
    TargetState,
)


def item(id, type_, statement, *, source="SRC-1", certainty=InterpretationCertainty.EXPLICIT, line=1, section=None):
    return interpreted_item(
        item_id=id,
        item_type=type_,
        statement=statement,
        certainty=certainty,
        source_id=source,
        location=SourceLocation(f"{source}:{line}", line, line, section=section),
    )


@pytest.mark.parametrize("type_,statement", [
    (InterpretationType.PERMISSION, "El administrador puede bloquear una cuenta activa."),
    (InterpretationType.RESTRICTION, "El usuario no puede cancelar una compra aprobada."),
    (InterpretationType.TRANSITION, "El estado cambia de PENDIENTE a APROBADO."),
    (InterpretationType.BUSINESS_RULE, "La contraseña debe tener al menos 12 caracteres."),
    (InterpretationType.EXPECTED_BEHAVIOR, "La operación aprobada muestra confirmación."),
    (InterpretationType.DATA_CONSTRAINT, "La contraseña admite un máximo de 64 caracteres."),
])
def test_testable_interpretation_produces_coverage_unit(type_, statement):
    result = build_coverage_model(InterpretationResult(("SRC-1",), (item("I-1", type_, statement),)))
    assert len(result.coverage_units) == 1
    assert result.coverage_units[0].statement.startswith("Validar que ")


def test_isolated_actor_produces_no_coverage_unit():
    result = build_coverage_model(InterpretationResult(("SRC-1",), (item("I-1", InterpretationType.ACTOR, "Administrador"),)))
    assert result.coverage_units == ()
    assert result.diagnostics[0].type is CoverageDiagnosticType.NON_COVERABLE


def test_descriptive_state_without_obligation_produces_no_coverage_unit():
    result = build_coverage_model(InterpretationResult(("SRC-1",), (item("I-1", InterpretationType.STATE, "Estado APROBADO"),)))
    assert result.coverage_units == ()


def test_coverage_preserves_source_location_and_neutral_domain_states():
    source_item = item("I-1", InterpretationType.PERMISSION, "El administrador puede bloquear una cuenta.", source="SRC-9", line=42, section="Permisos")
    result = build_coverage_model(InterpretationResult(("SRC-9",), (source_item,)))
    unit, origin = result.coverage_units[0], result.traceability[0]
    assert unit.source_refs == ("SRC-9",)
    assert origin.locations[0].line_start == 42
    assert origin.locations[0].section == "Permisos"
    assert unit.importance is Importance.NOT_JUSTIFIED
    assert unit.existing_coverage is ExistingCoverage.NOT_EVALUABLE
    assert unit.target_state is TargetState.NOT_SELECTED


def test_actor_behavior_condition_can_compose_one_coverage_unit():
    items = (
        item("A", InterpretationType.ACTOR, "El usuario", line=1),
        item("B", InterpretationType.BEHAVIOR, "puede cancelar una reserva", line=2),
        item("C", InterpretationType.CONDITION, "hasta 24 horas antes del turno", line=3),
    )
    result = build_coverage_model(InterpretationResult(("SRC-1",), items))
    assert len(result.coverage_units) == 1
    assert result.traceability[0].interpreted_item_ids == ("B", "A", "C")
    assert "24 horas" in result.coverage_units[0].statement


def test_identical_obligation_from_two_sources_deduplicates_and_keeps_both_sources():
    items = (
        item("A", InterpretationType.PERMISSION, "El administrador puede bloquear una cuenta.", source="SRC-1"),
        item("B", InterpretationType.PERMISSION, "El administrador puede bloquear una cuenta.", source="SRC-2"),
    )
    result = build_coverage_model(InterpretationResult(("SRC-1", "SRC-2"), items))
    assert len(result.coverage_units) == 1
    assert result.coverage_units[0].source_refs == ("SRC-1", "SRC-2")
    assert result.traceability[0].interpreted_item_ids == ("A", "B")


def test_similar_but_different_obligations_are_not_merged():
    items = (
        item("A", InterpretationType.PERMISSION, "El administrador puede bloquear una cuenta activa."),
        item("B", InterpretationType.PERMISSION, "El administrador puede desbloquear una cuenta activa."),
    )
    result = build_coverage_model(InterpretationResult(("SRC-1",), items))
    assert len(result.coverage_units) == 2
    assert [unit.id for unit in result.coverage_units] == ["UC-001", "UC-002"]


def test_inferred_origin_remains_inferred():
    result = build_coverage_model(InterpretationResult(("SRC-1",), (
        item("I", InterpretationType.BEHAVIOR, "El usuario edita su perfil", certainty=InterpretationCertainty.INFERRED),
    )))
    assert result.traceability[0].certainties == (InterpretationCertainty.INFERRED,)


def test_ambiguous_obligation_creates_traced_definition_gap():
    source_item = item("I", InterpretationType.BEHAVIOR, "La reserva vencida puede procesarse", certainty=InterpretationCertainty.AMBIGUOUS, source="SRC-7", line=8)
    result = build_coverage_model(InterpretationResult(("SRC-7",), (source_item,)))
    unit = result.coverage_units[0]
    gap = result.definition_gaps[0]
    assert unit.designability is Designability.BLOCKED_BY_DEFINITION
    assert unit.definition_gap_ref == gap.id
    assert gap.source_refs == ("SRC-7",)
    assert gap.affected_coverage_units == (unit.id,)
    assert result.traceability[0].certainties == (InterpretationCertainty.AMBIGUOUS,)


def test_contradiction_creates_gap_without_choosing_a_rule():
    a = item("A", InterpretationType.BUSINESS_RULE, "Cancelación hasta 24h", source="SRC-A")
    b = item("B", InterpretationType.BUSINESS_RULE, "Cancelación hasta 48h", source="SRC-B")
    contradiction = Contradiction("CON-1", ("A", "B"), "Conflicting source statements")
    result = build_coverage_model(InterpretationResult(("SRC-A", "SRC-B"), (a, b), (contradiction,)))
    assert result.coverage_units == ()
    assert result.definition_gaps[0].source_refs == ("SRC-A", "SRC-B")
    assert result.definition_gaps[0].affected_coverage_units == ()
    assert result.diagnostics[0].type is CoverageDiagnosticType.CONTRADICTION
    assert "24h" not in result.definition_gaps[0].description
    assert "48h" not in result.definition_gaps[0].description


def test_critical_importance_requires_explicit_evidence():
    critical = item("A", InterpretationType.BUSINESS_RULE, "Esta operación es crítica para facturación.")
    neutral = item("B", InterpretationType.BEHAVIOR, "El usuario puede editar su nombre.")
    result = build_coverage_model(InterpretationResult(("SRC-1",), (critical, neutral)))
    assert result.coverage_units[0].importance is Importance.CRITICAL
    assert result.coverage_units[1].importance is Importance.NOT_JUSTIFIED


def test_stable_ids_are_reproducible_for_same_input():
    interpretation = InterpretationResult(("SRC-1",), (
        item("A", InterpretationType.PERMISSION, "El usuario puede editar."),
        item("B", InterpretationType.RESTRICTION, "El usuario no puede borrar."),
    ))
    first = build_coverage_model(interpretation)
    second = build_coverage_model(interpretation)
    assert [unit.id for unit in first.coverage_units] == [unit.id for unit in second.coverage_units] == ["UC-001", "UC-002"]


def test_coverage_model_stage_three_boundaries():
    result = build_coverage_model(InterpretationResult(("SRC-1",), (
        item("A", InterpretationType.PERMISSION, "El usuario puede editar."),
    )))
    unit = result.coverage_units[0]
    assert not hasattr(result, "tests")
    assert not hasattr(result, "target_selection")
    assert not hasattr(result, "existing_tests")
    assert not hasattr(result, "execution_requirements")
    assert unit.test_refs == ()
    assert unit.existing_coverage is ExistingCoverage.NOT_EVALUABLE
    assert unit.target_state is TargetState.NOT_SELECTED
