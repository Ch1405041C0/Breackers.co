from dataclasses import replace

from breakers.strike.coverage import CoverageModelResult
from breakers.strike.existing_coverage import ExistingCoverageDiagnosticType, MappingContribution, map_existing_coverage
from breakers.strike.ingestion import ingest_source
from breakers.strike.models import CoverageUnit, Designability, ExistingCoverage, Importance, Source, TargetState


def uc(id, statement, *, blocked=False):
    return CoverageUnit(
        id, statement, Importance.NOT_JUSTIFIED, ExistingCoverage.NOT_EVALUABLE,
        TargetState.NOT_SELECTED,
        Designability.BLOCKED_BY_DEFINITION if blocked else Designability.DESIGNABLE,
        source_refs=("REQ-1",),
        definition_gap_ref="GAP-1" if blocked else None,
    )


def coverage(*units):
    return CoverageModelResult(tuple(units), (), (), ())


def existing_existing_tests_source(csv_text, source_id="TESTS-1"):
    return ingest_source(Source(source_id, "EXISTING_TESTS"), "tests.csv", csv_text)


def assessment(result, unit_id):
    return next(item for item in result.assessments if item.coverage_unit_id == unit_id)


def test_explicit_existing_test_covers_unit_and_preserves_identity_and_row():
    unit = uc("UC-1", "Validar que el administrador puede bloquear una cuenta activa.")
    source = existing_tests_source("ID,Description,Preconditions,Steps,Expected Result\nTC-15,Bloquear cuenta activa como administrador,cuenta activa,administrador bloquea cuenta,la cuenta queda bloqueada")
    result = map_existing_coverage(coverage(unit), (source,))
    assert assessment(result, "UC-1").status is ExistingCoverage.COVERED
    assert result.existing_tests[0].original_id == "TC-15"
    assert result.existing_tests[0].original_row["ID"] == "TC-15"
    assert result.mappings[0].coverage_unit_id == "UC-1"
    assert result.mappings[0].evidence


def test_behavior_matches_but_missing_state_is_partial():
    unit = uc("UC-1", "Validar que el usuario no puede cancelar una compra APROBADA.")
    source = existing_tests_source("ID,Description,Steps,Expected Result\nTC-20,Validar cancelación de compra,usuario cancela compra,cancelación rechazada")
    result = map_existing_coverage(coverage(unit), (source,))
    mapped = assessment(result, "UC-1")
    assert mapped.status is ExistingCoverage.PARTIAL
    assert "aprobada" in mapped.missing_aspects


def test_wrong_actor_does_not_declare_covered():
    unit = uc("UC-1", "Validar que el administrador puede bloquear una cuenta activa.")
    source = existing_tests_source("ID,Description,Preconditions,Steps,Expected Result\nTC-1,Bloquear cuenta activa como usuario,cuenta activa,usuario bloquea cuenta,cuenta bloqueada")
    assert assessment(map_existing_coverage(coverage(unit), (source,)), "UC-1").status is not ExistingCoverage.COVERED


def test_missing_expected_result_does_not_declare_covered():
    unit = uc("UC-1", "Validar que el administrador puede bloquear una cuenta activa.")
    source = existing_tests_source("ID,Description,Preconditions,Steps\nTC-1,Bloquear cuenta activa como administrador,cuenta activa,administrador bloquea cuenta")
    assert assessment(map_existing_coverage(coverage(unit), (source,)), "UC-1").status is ExistingCoverage.PARTIAL


def test_multiple_tests_can_jointly_cover_one_unit():
    unit = uc("UC-1", "Validar que el usuario puede cancelar una reserva hasta 24h antes.")
    source = existing_tests_source("ID,Description,Steps,Expected Result\nA,Usuario cancela reserva,usuario cancela reserva,cancelación permitida\nB,Cancelación 24h antes,cancelar reserva hasta 24h antes,cancelación permitida")
    result = map_existing_coverage(coverage(unit), (source,))
    assert assessment(result, "UC-1").status is ExistingCoverage.COVERED
    assert len(assessment(result, "UC-1").existing_test_ids) == 2


def test_one_test_can_map_to_multiple_units():
    units = (
        uc("UC-1", "Validar que el administrador puede bloquear una cuenta activa."),
        uc("UC-2", "Validar que una cuenta activa queda bloqueada."),
    )
    source = existing_tests_source("ID,Description,Preconditions,Steps,Expected Result\nTC-1,Bloquear cuenta activa como administrador,cuenta activa,administrador bloquea cuenta,cuenta activa queda bloqueada")
    result = map_existing_coverage(coverage(*units), (source,))
    assert {mapping.coverage_unit_id for mapping in result.mappings} == {"UC-1", "UC-2"}


def test_no_related_test_in_evaluable_set_is_uncovered():
    unit = uc("UC-1", "Validar que la contraseña debe contener al menos 12 caracteres.")
    source = existing_tests_source("ID,Description,Steps,Expected Result\nT1,Login válido,ingresar credenciales,acceso\nT2,Logout,cerrar sesión,sesión cerrada\nT3,Recuperar contraseña,solicitar recuperación,email enviado")
    result = map_existing_coverage(coverage(unit), (source,))
    assert assessment(result, "UC-1").status is ExistingCoverage.UNCOVERED


def test_superficial_similarity_does_not_equal_coverage():
    unit = uc("UC-1", "Validar que el administrador puede bloquear una cuenta activa.")
    source = existing_tests_source("ID,Description,Steps,Expected Result\nT1,Consultar cuenta activa,consultar cuenta,datos visibles")
    assert assessment(map_existing_coverage(coverage(unit), (source,)), "UC-1").status is ExistingCoverage.UNCOVERED


def test_insufficient_test_information_is_not_evaluable():
    unit = uc("UC-1", "Validar que la contraseña debe contener al menos 12 caracteres.")
    source = existing_tests_source("ID,Description\nTC-55,Probar contraseña")
    result = map_existing_coverage(coverage(unit), (source,))
    assert assessment(result, "UC-1").status is ExistingCoverage.NOT_EVALUABLE


def test_blocked_unit_is_not_evaluable_even_if_test_matches():
    unit = uc("UC-1", "Validar cancelación de reserva.", blocked=True)
    source = existing_tests_source("ID,Description,Steps,Expected Result\nTC-1,Cancelación de reserva,cancelar,reserva cancelada")
    result = map_existing_coverage(coverage(unit), (source,))
    assert assessment(result, "UC-1").status is ExistingCoverage.NOT_EVALUABLE


def test_ambiguous_csv_mapping_cannot_create_false_coverage_and_preserves_unknown_column():
    unit = uc("UC-1", "Validar que el administrador puede bloquear una cuenta activa.")
    source = existing_tests_source("ID,Description,Steps,Expected Result,MagicColumn\nTC-1,Bloquear cuenta activa como administrador,bloquear,cuenta bloqueada,keep-me")
    result = map_existing_coverage(coverage(unit), (source,))
    assert assessment(result, "UC-1").status is ExistingCoverage.NOT_EVALUABLE
    assert result.existing_tests[0].original_row["MagicColumn"] == "keep-me"
    assert any(d.type is ExistingCoverageDiagnosticType.AMBIGUOUS_TEST_SCHEMA for d in result.diagnostics)


def test_unmapped_test_is_preserved_and_not_called_useless():
    unit = uc("UC-1", "Validar que el administrador puede bloquear una cuenta activa.")
    source = existing_tests_source("ID,Description,Steps,Expected Result\nLEGACY-9,Exportar reporte,exportar,reporte creado")
    result = map_existing_coverage(coverage(unit), (source,))
    assert result.existing_tests[0].original_id == "LEGACY-9"
    assert result.unmapped_test_ids == ("TESTS-1:LEGACY-9",)
    diagnostic = next(d for d in result.diagnostics if d.type is ExistingCoverageDiagnosticType.UNMAPPED_TEST)
    assert "useless" not in diagnostic.statement.lower()
    assert "inútil" not in diagnostic.statement.lower()


def test_possible_redundancy_is_only_a_diagnostic():
    unit = uc("UC-1", "Validar que el administrador puede bloquear una cuenta activa.")
    source = existing_tests_source("ID,Description,Preconditions,Steps,Expected Result\nA,Bloquear cuenta activa como administrador,cuenta activa,bloquear,cuenta bloqueada\nB,Bloquear cuenta activa como administrador,cuenta activa,bloquear,cuenta bloqueada")
    result = map_existing_coverage(coverage(unit), (source,))
    assert len(result.existing_tests) == 2
    assert any(d.type is ExistingCoverageDiagnosticType.POSSIBLE_REDUNDANCY for d in result.diagnostics)


def test_mapping_certainty_is_never_artificially_elevated_for_partial():
    unit = uc("UC-1", "Validar que el usuario no puede cancelar una compra APROBADA.")
    source = existing_tests_source("ID,Description,Steps,Expected Result\nTC-20,Cancelación de compra,usuario cancela compra,cancelación rechazada")
    result = map_existing_coverage(coverage(unit), (source,))
    assert result.mappings[0].contribution is MappingContribution.PARTIAL
    assert result.mappings[0].certainty.value == "INFERRED"


def test_no_duplicate_mappings_are_generated():
    unit = uc("UC-1", "Validar que el administrador puede bloquear una cuenta activa.")
    source = existing_tests_source("ID,Description,Preconditions,Steps,Expected Result\nTC-1,Bloquear cuenta activa como administrador,cuenta activa,bloquear,cuenta bloqueada")
    result = map_existing_coverage(coverage(unit), (source,))
    pairs = [(m.coverage_unit_id, m.existing_test_id) for m in result.mappings]
    assert len(pairs) == len(set(pairs))


def test_mapping_does_not_mutate_coverage_universe_or_create_future_stage_objects():
    original = uc("UC-1", "Validar que el administrador puede bloquear una cuenta activa.")
    source = existing_tests_source("ID,Description,Preconditions,Steps,Expected Result\nTC-1,Bloquear cuenta activa como administrador,cuenta activa,bloquear,cuenta bloqueada")
    model = coverage(original)
    result = map_existing_coverage(model, (source,))
    assert model.coverage_units == (original,)
    assert model.coverage_units[0].existing_coverage is ExistingCoverage.NOT_EVALUABLE
    assert not hasattr(result, "coverage_units")
    assert not hasattr(result, "target_selection")
    assert not hasattr(result, "designed_tests")
    assert not hasattr(result, "execution_requirements")
    assert not hasattr(result, "dependencies")
