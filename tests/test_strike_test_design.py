from breakers.strike.coverage import CoverageModelResult, CoverageOrigin
from breakers.strike.existing_coverage import (
    CoverageAssessment,
    CoverageMapping,
    ExistingCoverageResult,
    ExistingTestEvidence,
    MappingContribution,
)
from breakers.strike.ingestion import SourceLocation
from breakers.strike.interpretation import InterpretationCertainty
from breakers.strike.models import (
    ClientExclusion,
    CoverageUnit,
    DefinitionGap,
    Designability,
    ExistingCoverage,
    Importance,
    TargetSelection,
    TargetState,
    TestOrigin,
)
from breakers.strike.target_selection import TargetSelectionResult
from breakers.strike.test_design import TestDesignDiagnosticType, design_tests


def unit(uid, statement, status, *, blocked=False):
    return CoverageUnit(
        uid, statement, Importance.NOT_JUSTIFIED, status, TargetState.NOT_SELECTED,
        Designability.BLOCKED_BY_DEFINITION if blocked else Designability.DESIGNABLE,
        source_refs=("SRC-1",), definition_gap_ref="GAP-1" if blocked else None,
    )


def coverage(*units):
    origins = tuple(
        CoverageOrigin(u.id, (f"INT-{i}",), ("SRC-1",), (SourceLocation("req.md / line 1", 1, 1),), (InterpretationCertainty.EXPLICIT,))
        for i, u in enumerate(units, 1)
    )
    gaps = (DefinitionGap("GAP-1", "Missing expected behavior", ("SRC-1",), (units[0].id,)),) if units and units[0].definition_gap_ref else ()
    return CoverageModelResult(tuple(units), gaps, origins, ())


def existing_result(units, assessments, tests=(), mappings=()):
    return ExistingCoverageResult(tuple(assessments), tuple(mappings), tuple(tests), (), ())


def target(units, selected, exclusions=()):
    selection = TargetSelection(100, round(len(selected) / len(units) * 100) if units else 0, tuple(selected), tuple(e.id for e in exclusions))
    return TargetSelectionResult(selection, tuple(u.id for u in units), tuple(selected), tuple(u.id for u in units if u.id not in selected), tuple(exclusions), (), ())


def test_covered_reuses_existing_without_new_test_and_preserves_identity():
    u = unit("UC-001", "Validar que el administrador puede bloquear una cuenta activa.", ExistingCoverage.COVERED)
    old = ExistingTestEvidence("SRC-T:TC-20", "TC-20", "SRC-T", {"ID": "TC-20", "Steps": "bloquear"}, "Bloquear cuenta", steps="bloquear", expected_result="cuenta bloqueada")
    assessment = CoverageAssessment(u.id, ExistingCoverage.COVERED, (old.internal_id,), ("steps: bloquear",), ())
    mapping = CoverageMapping(u.id, old.internal_id, MappingContribution.FULL, ("steps: bloquear",), (), InterpretationCertainty.EXPLICIT)
    result = design_tests(coverage(u), existing_result((u,), (assessment,), (old,), (mapping,)), target((u,), (u.id,)))
    assert result.designed_tests == ()
    assert result.existing_tests[0] == old
    assert result.existing_tests[0].original_id == "TC-20"
    assert result.coverage_links[0].test_id == old.internal_id


def test_partial_design_focuses_only_on_missing_aspect():
    u = unit("UC-001", "Validar que el usuario no puede cancelar una compra aprobada.", ExistingCoverage.PARTIAL)
    assessment = CoverageAssessment(u.id, ExistingCoverage.PARTIAL, ("T-1",), (), ("aprobada",))
    result = design_tests(coverage(u), existing_result((u,), (assessment,)), target((u,), (u.id,)))
    assert len(result.designed_tests) == 1
    designed = result.designed_tests[0]
    assert designed.origin is TestOrigin.STRIKE_COMPLEMENTED
    assert designed.preconditions == ("aprobada",)
    assert "aprobada" in designed.description.lower()
    assert designed.covers == (u.id,)


def test_uncovered_designs_new_test_when_definition_supports_it():
    u = unit("UC-001", "Validar que el administrador puede bloquear una cuenta activa.", ExistingCoverage.UNCOVERED)
    assessment = CoverageAssessment(u.id, ExistingCoverage.UNCOVERED, (), (), ())
    result = design_tests(coverage(u), existing_result((u,), (assessment,)), target((u,), (u.id,)))
    assert len(result.designed_tests) == 1
    assert result.designed_tests[0].origin is TestOrigin.STRIKE_GENERATED
    assert "activa" in result.designed_tests[0].preconditions


def test_not_evaluable_remains_not_evaluable_but_can_design_from_definition():
    u = unit("UC-001", "Validar que el administrador puede bloquear una cuenta activa.", ExistingCoverage.NOT_EVALUABLE)
    assessment = CoverageAssessment(u.id, ExistingCoverage.NOT_EVALUABLE, (), (), ("existing tests are not evaluable",))
    existing = existing_result((u,), (assessment,))
    result = design_tests(coverage(u), existing, target((u,), (u.id,)))
    assert len(result.designed_tests) == 1
    assert existing.assessments[0].status is ExistingCoverage.NOT_EVALUABLE
    assert any(d.type is TestDesignDiagnosticType.EXISTING_COVERAGE_NOT_EVALUABLE for d in result.diagnostics)


def test_unselected_and_client_excluded_units_create_no_tests():
    u1 = unit("UC-001", "Validar que el usuario puede cancelar una reserva.", ExistingCoverage.UNCOVERED)
    u2 = unit("UC-002", "Validar que el administrador puede bloquear una cuenta.", ExistingCoverage.UNCOVERED)
    assessments = (CoverageAssessment(u1.id, u1.existing_coverage, (), (), ()), CoverageAssessment(u2.id, u2.existing_coverage, (), (), ()))
    exclusion = ClientExclusion("EX-1", u2.id, "client")
    result = design_tests(coverage(u1, u2), existing_result((u1, u2), assessments), target((u1, u2), (u1.id,), (exclusion,)))
    assert {t.covers for t in result.designed_tests} == {(u1.id,)}


def test_blocked_selected_unit_preserves_gap_and_does_not_invent_test():
    u = unit("UC-001", "Validar que la API requiere API Key.", ExistingCoverage.NOT_EVALUABLE, blocked=True)
    assessment = CoverageAssessment(u.id, ExistingCoverage.NOT_EVALUABLE, (), (), ())
    result = design_tests(coverage(u), existing_result((u,), (assessment,)), target((u,), (u.id,)))
    assert result.designed_tests == ()
    assert result.blocked_unit_ids == (u.id,)
    assert result.definition_gaps[0].id == "GAP-1"
    assert result.diagnostics[0].type is TestDesignDiagnosticType.BLOCKED_BY_DEFINITION


def test_expected_result_never_invents_http_status_for_api_key_requirement():
    u = unit("UC-001", "Validar que la API requiere API Key.", ExistingCoverage.UNCOVERED)
    assessment = CoverageAssessment(u.id, ExistingCoverage.UNCOVERED, (), (), ())
    result = design_tests(coverage(u), existing_result((u,), (assessment,)), target((u,), (u.id,)))
    assert len(result.designed_tests) == 1
    expected = result.designed_tests[0].expected_result
    assert "API Key" in expected
    assert "401" not in expected and "403" not in expected and "expired" not in expected


def test_designed_ids_and_output_are_deterministic():
    u = unit("UC-001", "Validar que el usuario no puede cancelar una compra aprobada.", ExistingCoverage.UNCOVERED)
    assessment = CoverageAssessment(u.id, ExistingCoverage.UNCOVERED, (), (), ())
    args = (coverage(u), existing_result((u,), (assessment,)), target((u,), (u.id,)))
    first = design_tests(*args)
    second = design_tests(*args)
    assert first.designed_tests == second.designed_tests
    assert first.designed_tests[0].id.startswith("STR-")


def test_permission_and_restriction_semantics_are_preserved():
    permission = unit("UC-001", "Validar que el administrador puede bloquear una cuenta activa.", ExistingCoverage.UNCOVERED)
    restriction = unit("UC-002", "Validar que el usuario no puede cancelar una compra aprobada.", ExistingCoverage.UNCOVERED)
    assessments = tuple(CoverageAssessment(u.id, u.existing_coverage, (), (), ()) for u in (permission, restriction))
    result = design_tests(coverage(permission, restriction), existing_result((permission, restriction), assessments), target((permission, restriction), (permission.id, restriction.id)))
    by_uc = {t.covers[0]: t for t in result.designed_tests}
    assert "puede" in by_uc[permission.id].expected_result.lower()
    assert "no puede" in by_uc[restriction.id].expected_result.lower()


def test_transition_preserves_explicit_states():
    u = unit("UC-001", "Validar que el estado PENDING → APPROVED.", ExistingCoverage.UNCOVERED)
    assessment = CoverageAssessment(u.id, u.existing_coverage, (), (), ())
    result = design_tests(coverage(u), existing_result((u,), (assessment,)), target((u,), (u.id,)))
    assert "PENDING" in result.designed_tests[0].expected_result
    assert "APPROVED" in result.designed_tests[0].expected_result


def test_data_constraint_does_not_invent_additional_constraint():
    u = unit("UC-001", "Validar que el DNI debe tener 8 dígitos.", ExistingCoverage.UNCOVERED)
    assessment = CoverageAssessment(u.id, u.existing_coverage, (), (), ())
    result = design_tests(coverage(u), existing_result((u,), (assessment,)), target((u,), (u.id,)))
    expected = result.designed_tests[0].expected_result.lower()
    assert "8 dígitos" in expected
    assert "solo números" not in expected and "sólo números" not in expected


def test_explicit_boundary_is_preserved_without_inventing_another_limit():
    u = unit("UC-001", "Validar que el archivo debe tener máximo 10 MB.", ExistingCoverage.UNCOVERED)
    assessment = CoverageAssessment(u.id, u.existing_coverage, (), (), ())
    result = design_tests(coverage(u), existing_result((u,), (assessment,)), target((u,), (u.id,)))
    assert "10 MB" in result.designed_tests[0].expected_result
    assert "11 MB" not in result.designed_tests[0].expected_result


def test_insufficient_expected_behavior_blocks_design_instead_of_inventing():
    u = unit("UC-001", "Validar procesamiento del archivo.", ExistingCoverage.UNCOVERED)
    assessment = CoverageAssessment(u.id, u.existing_coverage, (), (), ())
    result = design_tests(coverage(u), existing_result((u,), (assessment,)), target((u,), (u.id,)))
    assert result.designed_tests == ()
    assert result.blocked_unit_ids == (u.id,)
    assert result.diagnostics[0].type is TestDesignDiagnosticType.INSUFFICIENT_EXPECTED_BEHAVIOR


def test_stage_does_not_mutate_inputs_or_create_executability_objects():
    u = unit("UC-001", "Validar que el usuario puede cancelar una reserva.", ExistingCoverage.UNCOVERED)
    assessment = CoverageAssessment(u.id, u.existing_coverage, (), (), ())
    cov = coverage(u)
    ext = existing_result((u,), (assessment,))
    tgt = target((u,), (u.id,))
    result = design_tests(cov, ext, tgt)
    assert cov.coverage_units == (u,)
    assert ext.assessments == (assessment,)
    assert tgt.selected_unit_ids == (u.id,)
    assert not hasattr(result, "execution_requirements")
    assert not hasattr(result, "dependencies")
    assert not hasattr(result, "executability")
    assert all(test.requires == () and test.produces == () and test.depends_on == () for test in result.designed_tests)


def test_every_designed_test_is_linked_to_selected_coverage_and_source_trace_remains():
    u = unit("UC-001", "Validar que el usuario puede cancelar una reserva.", ExistingCoverage.UNCOVERED)
    assessment = CoverageAssessment(u.id, u.existing_coverage, (), (), ())
    cov = coverage(u)
    result = design_tests(cov, existing_result((u,), (assessment,)), target((u,), (u.id,)))
    designed = result.designed_tests[0]
    assert designed.covers == (u.id,)
    assert any(link.test_id == designed.id and link.coverage_unit_ids == (u.id,) for link in result.coverage_links)
    origin = next(item for item in cov.traceability if item.coverage_unit_id == u.id)
    assert origin.source_ids == ("SRC-1",)
