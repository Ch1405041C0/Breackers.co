import pytest

from breakers.strike.models import ClientExclusion, CriticalSelectionPolicy, Source
from breakers.strike.pipeline import StrikePipelineStatus, StrikeSourceInput, run_strike


def definition(source_id, filename, content):
    return StrikeSourceInput(Source(source_id, "DEFINITION", filename), filename, content)


def existing(source_id, content):
    return StrikeSourceInput(Source(source_id, "EXISTING_TESTS", "existing.csv"), "existing.csv", content)


def test_pipeline_without_existing_tests_runs_full_chain():
    result = run_strike(
        (definition("REQ", "requirements.md", "# Rules\nEl administrador puede bloquear una cuenta activa."),),
        requested_target=100,
    )
    assert result.status is StrikePipelineStatus.COMPLETE
    assert result.coverage.coverage_units
    assert result.existing_coverage.existing_tests == ()
    assert result.target_selection.selection.requested_target == 100
    assert result.test_design is not None
    assert result.executability is not None


def test_existing_source_is_not_interpreted_as_definition_and_covered_is_reused():
    csv = "ID,Description,Preconditions,Steps,Expected Result\nTC-1,Bloquear cuenta,cuenta activa,administrador bloquea cuenta,cuenta bloqueada\n"
    result = run_strike(
        (definition("REQ", "requirements.md", "El administrador puede bloquear una cuenta activa."),),
        existing_test_sources=(existing("TESTS", csv),),
        requested_target=100,
    )
    assert result.interpretation.source_ids == ("REQ",)
    assert all(origin.source_ids == ("REQ",) for origin in result.coverage.traceability)
    assert result.existing_coverage.existing_tests[0].original_id == "TC-1"


@pytest.mark.parametrize("target", (25, 50, 75, 100))
def test_pipeline_delegates_each_supported_target(target):
    definitions = tuple(
        definition(f"REQ-{i}", f"r{i}.txt", f"El usuario puede cancelar la reserva {i}.")
        for i in range(1, 5)
    )
    result = run_strike(definitions, requested_target=target)
    assert result.target_selection.selection.requested_target == target
    assert result.target_selection.selection.effective_target == target


def test_client_exclusion_survives_and_prevents_test_design():
    definitions = (
        definition("A", "a.txt", "El usuario puede cancelar una reserva."),
        definition("B", "b.txt", "El administrador puede bloquear una cuenta."),
    )
    exclusion = ClientExclusion("EX-1", "UC-002", "client choice")
    result = run_strike(definitions, requested_target=100, exclusions=(exclusion,))
    assert "UC-002" in result.target_selection.universe_unit_ids
    assert "UC-002" not in result.target_selection.selected_unit_ids
    assert result.target_selection.selection.exclusions == ("EX-1",)
    assert all("UC-002" not in test.covers for test in result.test_design.designed_tests)


def test_critical_conflict_pauses_without_silently_choosing_policy():
    definitions = tuple(
        definition(f"C-{i}", f"c{i}.txt", f"Regla crítica: el usuario puede cancelar reserva {i}.")
        for i in range(1, 3)
    ) + tuple(
        definition(f"N-{i}", f"n{i}.txt", f"El usuario puede consultar reserva {i}.")
        for i in range(1, 7)
    )
    result = run_strike(definitions, requested_target=25)
    assert result.status is StrikePipelineStatus.ACTION_REQUIRED
    assert result.target_selection is None
    assert result.test_design is None
    assert result.executability is None
    assert any(item.stage == "TARGET_SELECTION" for item in result.diagnostics)


@pytest.mark.parametrize("policy", (CriticalSelectionPolicy.INCLUDE_ALL_CRITICAL, CriticalSelectionPolicy.RESPECT_REQUESTED_TARGET))
def test_critical_conflict_continues_with_explicit_policy(policy):
    definitions = tuple(
        definition(f"C-{i}", f"c{i}.txt", f"Regla crítica: el usuario puede cancelar reserva {i}.")
        for i in range(1, 3)
    ) + tuple(
        definition(f"N-{i}", f"n{i}.txt", f"El usuario puede consultar reserva {i}.")
        for i in range(1, 7)
    )
    result = run_strike(definitions, requested_target=25, critical_policy=policy)
    assert result.status is StrikePipelineStatus.COMPLETE
    assert result.target_selection.selection.critical_policy is policy


def test_multiple_definition_sources_keep_source_identity():
    result = run_strike(
        (
            definition("REQ-A", "a.md", "# A\nEl usuario puede cancelar una reserva."),
            definition("REQ-B", "b.txt", "El administrador puede bloquear una cuenta activa."),
        ),
        requested_target=100,
    )
    assert result.interpretation.source_ids == ("REQ-A", "REQ-B")
    assert {source.source_id for source in result.definition_sources} == {"REQ-A", "REQ-B"}


def test_pipeline_is_deterministic_and_does_not_mutate_inputs():
    inputs = (definition("REQ", "requirements.txt", "El administrador puede bloquear una cuenta activa."),)
    before = inputs
    first = run_strike(inputs, requested_target=100)
    second = run_strike(inputs, requested_target=100)
    assert first == second
    assert inputs == before


def test_empty_definitions_fail_clearly():
    with pytest.raises(ValueError, match="at least one definition source"):
        run_strike((), requested_target=100)


def test_wrong_source_channel_fails_instead_of_cross_contaminating():
    csv = "ID,Description,Steps,Expected Result\nTC-1,Bloquear,bloquear,bloqueada\n"
    with pytest.raises(ValueError, match="existing-test sources"):
        run_strike((existing("TESTS", csv),), requested_target=100)


def test_result_is_inspectable_without_reexecution_and_has_no_side_effect_surfaces():
    result = run_strike(
        (definition("REQ", "requirements.txt", "El usuario puede cancelar una reserva."),),
        requested_target=100,
    )
    assert result.interpretation is not None
    assert result.coverage is not None
    assert result.existing_coverage is not None
    assert result.target_selection is not None
    assert result.test_design is not None
    assert result.executability is not None
    assert not hasattr(result, "report")
    assert not hasattr(result, "payment")
    assert not hasattr(result, "http")
    assert not hasattr(result, "execution_results")


def test_diagnostics_keep_stage_origin():
    result = run_strike(
        (definition("REQ", "requirements.txt", "El administrador puede bloquear una cuenta activa."),),
        requested_target=100,
    )
    assert all(item.stage in {"INTERPRETATION", "COVERAGE", "EXISTING_COVERAGE", "TARGET_SELECTION", "TEST_DESIGN", "EXECUTABILITY"} for item in result.diagnostics)
