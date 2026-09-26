from copy import deepcopy
from dataclasses import replace

import pytest

from breakers.strike.deliverable import (
    DeliverableBuilder,
    DeliverableColumnConfiguration,
    DeliverableConfiguration,
    DeliverableContentFilter,
    DeliverableDecisionRequired,
    DeliverableField,
    DeliverableFormat,
    DeliverableMode,
    DeliverableSectionConfiguration,
)
from breakers.strike.models import DefinitionGap, Source, TestOrigin
from breakers.strike.pipeline import StrikeSourceInput, run_strike


def definition(source_id, text):
    return StrikeSourceInput(Source(source_id, "DEFINITION", f"{source_id}.txt"), f"{source_id}.txt", text)


def existing_csv(content):
    return StrikeSourceInput(Source("TESTS", "EXISTING_TESTS", "tests.csv"), "tests.csv", content)


def complete_result():
    return run_strike(
        (definition("REQ", "El administrador puede bloquear una cuenta activa."),),
        requested_target=100,
    )


def custom(*columns, filter_=None, name="Custom"):
    return DeliverableConfiguration(
        DeliverableMode.CUSTOM,
        DeliverableFormat.CSV,
        (DeliverableSectionConfiguration("custom", name, filter_ or DeliverableContentFilter(), tuple(columns)),),
    )


def test_breakers_recommended_produces_valid_neutral_projection():
    result = complete_result()
    config = DeliverableConfiguration.breakers_recommended()
    deliverable = DeliverableBuilder().build(result, config)
    assert deliverable.format is DeliverableFormat.XLSX
    assert [section.name for section in deliverable.sections] == ["Plan de pruebas", "Definition Gaps", "Requisitos de ejecución"]
    assert deliverable.sections[0].rows


def test_custom_respects_columns_order_and_aliases():
    result = complete_result()
    config = custom(
        DeliverableColumnConfiguration(DeliverableField.EXPECTED_RESULT, "Validación"),
        DeliverableColumnConfiguration(DeliverableField.TEST_ID, "Nro."),
        DeliverableColumnConfiguration(DeliverableField.TEST_DESCRIPTION, "Detalle"),
    )
    section = DeliverableBuilder().build(result, config).sections[0]
    assert section.columns == ("Validación", "Nro.", "Detalle")
    assert section.fields == (DeliverableField.EXPECTED_RESULT, DeliverableField.TEST_ID, DeliverableField.TEST_DESCRIPTION)


def test_filters_and_multiple_sections_only_select_presentation():
    result = complete_result()
    generated = DeliverableSectionConfiguration(
        "generated", "Generados",
        DeliverableContentFilter(test_origins=(TestOrigin.STRIKE_GENERATED,)),
        (DeliverableColumnConfiguration(DeliverableField.TEST_ORIGIN, "Origen"),),
    )
    existing = DeliverableSectionConfiguration(
        "existing", "Existentes",
        DeliverableContentFilter(test_origins=(TestOrigin.EXISTING,)),
        (DeliverableColumnConfiguration(DeliverableField.TEST_ORIGIN, "Origen"),),
    )
    deliverable = DeliverableBuilder().build(
        result,
        DeliverableConfiguration(DeliverableMode.CUSTOM, DeliverableFormat.XLSX, (generated, existing)),
    )
    assert deliverable.sections[0].rows
    assert deliverable.sections[1].rows == ()


def test_hiding_field_does_not_modify_strike_result_and_build_is_deterministic():
    result = complete_result()
    before = deepcopy(result)
    config = custom(DeliverableColumnConfiguration(DeliverableField.TEST_ID, "ID"))
    first = DeliverableBuilder().build(result, config)
    second = DeliverableBuilder().build(result, config)
    assert first == second
    assert result == before
    assert first.sections[0].fields == (DeliverableField.TEST_ID,)


def test_existing_test_preserves_original_identity():
    csv = "ID,Description,Preconditions,Steps,Expected Result\nCLIENT-77,Bloquear cuenta,cuenta activa,administrador bloquea cuenta,cuenta bloqueada\n"
    result = run_strike(
        (definition("REQ", "El administrador puede bloquear una cuenta activa."),),
        existing_test_sources=(existing_csv(csv),),
        requested_target=100,
    )
    config = custom(
        DeliverableColumnConfiguration(DeliverableField.TEST_ID, "ID"),
        DeliverableColumnConfiguration(DeliverableField.TEST_ORIGIN, "Origen"),
    )
    rows = DeliverableBuilder().build(result, config).sections[0].rows
    assert any(row.values == ("CLIENT-77", "EXISTING") for row in rows)


def test_generated_origin_is_preserved():
    result = complete_result()
    config = custom(DeliverableColumnConfiguration(DeliverableField.TEST_ORIGIN, "Origen"))
    values = [row.values[0] for row in DeliverableBuilder().build(result, config).sections[0].rows]
    assert TestOrigin.STRIKE_GENERATED.value in values


def test_partial_existing_preserves_complemented_origin_when_domain_produces_it():
    csv = "ID,Description,Preconditions,Steps,Expected Result\nTC-1,Cancelar compra,compra aprobada,cancelar compra,\n"
    result = run_strike(
        (definition("REQ", "El usuario no puede cancelar una compra aprobada."),),
        existing_test_sources=(existing_csv(csv),),
        requested_target=100,
    )
    origins = {test.origin for test in result.test_design.designed_tests}
    assert TestOrigin.STRIKE_COMPLEMENTED in origins
    config = custom(DeliverableColumnConfiguration(DeliverableField.TEST_ORIGIN, "Origen"))
    projected = {row.values[0] for row in DeliverableBuilder().build(result, config).sections[0].rows}
    assert TestOrigin.STRIKE_COMPLEMENTED.value in projected


def test_definition_gap_stays_gap_and_is_not_converted_to_test():
    result = complete_result()
    unit = result.coverage.coverage_units[0]
    gap = DefinitionGap("GAP-X", "Falta definir el comportamiento esperado.", unit.source_refs, (unit.id,))
    result = replace(result, coverage=replace(result.coverage, definition_gaps=(gap,)))
    gap_section = DeliverableSectionConfiguration(
        "gaps", "Gaps",
        DeliverableContentFilter(include_tests=False, include_definition_gaps=True),
        (
            DeliverableColumnConfiguration(DeliverableField.DEFINITION_GAP, "Gap"),
            DeliverableColumnConfiguration(DeliverableField.TEST_ID, "Test"),
        ),
    )
    deliverable = DeliverableBuilder().build(
        result, DeliverableConfiguration(DeliverableMode.CUSTOM, DeliverableFormat.CSV, (gap_section,))
    )
    for row in deliverable.sections[0].rows:
        assert row.values[1] == ""


def test_target_is_explicitly_selected_scope_not_quality():
    result = complete_result()
    config = custom(DeliverableColumnConfiguration(DeliverableField.TARGET_SCOPE, "Alcance"))
    value = DeliverableBuilder().build(result, config).sections[0].rows[0].values[0]
    assert value.endswith("selected scope")
    assert "quality" not in value.lower() and "calidad" not in value.lower()


def test_generated_test_does_not_invent_input_data():
    result = complete_result()
    config = custom(DeliverableColumnConfiguration(DeliverableField.INPUT_DATA, "Datos"))
    assert all(row.values == ("",) for row in DeliverableBuilder().build(result, config).sections[0].rows)


def test_unmapped_template_column_can_remain_empty_in_neutral_deliverable():
    result = complete_result()
    config = custom(DeliverableColumnConfiguration(None, "Responsable QA", template_column_name="Responsable QA"))
    assert DeliverableBuilder().build(result, config).sections[0].rows[0].values == ("",)


def test_action_required_is_domain_decision_not_final_deliverable():
    definitions = tuple(
        definition(f"C-{i}", f"Regla crítica: el usuario puede cancelar reserva {i}.")
        for i in range(1, 5)
    ) + tuple(
        definition(f"N-{i}", f"El usuario puede consultar reserva {i}.")
        for i in range(1, 7)
    )
    result = run_strike(definitions, requested_target=25)
    with pytest.raises(DeliverableDecisionRequired, match="client decision"):
        DeliverableBuilder().build(result, DeliverableConfiguration.breakers_recommended())


def test_complete_can_produce_deliverable():
    deliverable = DeliverableBuilder().build(complete_result(), DeliverableConfiguration.breakers_recommended())
    assert deliverable.sections
