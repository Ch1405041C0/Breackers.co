import pytest

from breakers.strike.models import Source
from breakers.strike.ingestion import SourceFormat, UnsupportedSourceFormat, ingest_source
from breakers.strike.interpretation import (
    InterpretationCertainty,
    InterpretationResult,
    InterpretationType,
    find_contradictions,
    interpret_deterministically,
    interpreted_item,
)


def source(kind="BUSINESS_RULES"):
    return Source("SRC-001", kind, "client")


def test_ingests_txt_markdown_and_csv_and_preserves_source_id():
    txt = ingest_source(source(), "rules.txt", "El usuario puede cancelar.")
    md = ingest_source(source(), "rules.md", "# Cancelación\nEl usuario puede cancelar.")
    csv = ingest_source(source("EXISTING_TESTS"), "tests.csv", "Caso,Descripción,Entrada,Salida\nTC-1,Compra,1,OK")
    assert (txt.format, md.format, csv.format) == (SourceFormat.TEXT, SourceFormat.MARKDOWN, SourceFormat.CSV)
    assert txt.source_id == md.source_id == csv.source_id == "SRC-001"


def test_rejects_unsupported_and_empty_sources():
    with pytest.raises(UnsupportedSourceFormat):
        ingest_source(source(), "rules.pdf", "content")
    with pytest.raises(ValueError, match="empty"):
        ingest_source(source(), "rules.md", "   ")


def test_markdown_preserves_sections_and_locations():
    normalized = ingest_source(source(), "rules.md", "# Uno\nRegla A\n## Dos\nRegla B")
    assert [section.heading for section in normalized.sections] == ["Uno", "Dos"]
    assert normalized.sections[0].location.line_start == 1
    assert normalized.sections[1].location.section == "Dos"


def test_csv_preserves_headers_rows_and_original_row_values():
    normalized = ingest_source(source("EXISTING_TESTS"), "tests.csv", "ID,Preconditions,Steps,Expected Result,Priority\nTC-9,login,click,success,high")
    assert normalized.csv_columns == ("ID", "Preconditions", "Steps", "Expected Result", "Priority")
    assert normalized.csv_rows[0]["ID"] == "TC-9"
    assert normalized.existing_tests.rows[0]["Expected Result"] == "success"


@pytest.mark.parametrize("header", [
    "Caso,Descripción,Entrada,Salida\nTC1,Compra,uno,OK",
    "ID,Preconditions,Steps,Expected Result,Priority\nTC1,login,click,OK,high",
    "Historia,Escenario,Given,When,Then\nHU1,Compra,stock,comprar,confirmada",
])
def test_existing_tests_accept_client_csv_schemas(header):
    table = ingest_source(source("EXISTING_TESTS"), "tests.csv", header).existing_tests
    assert table is not None
    assert len(table.rows) == 1
    assert table.proposed_mapping


def test_unknown_csv_columns_are_preserved_and_not_mapped():
    table = ingest_source(source("EXISTING_TESTS"), "tests.csv", "ID,MagicColumn\nTC1,value").existing_tests
    assert table.rows[0]["MagicColumn"] == "value"
    assert "MagicColumn" in table.unmapped_columns
    assert table.mapping_confidence["MagicColumn"] == "AMBIGUOUS"
    assert "MagicColumn" not in table.proposed_mapping


def test_explicit_interpretation_keeps_source_and_location():
    normalized = ingest_source(source(), "rules.md", "# Permisos\nEl administrador puede bloquear una cuenta activa.")
    result = interpret_deterministically((normalized,))
    item = result.items[0]
    assert item.type is InterpretationType.PERMISSION
    assert item.certainty is InterpretationCertainty.EXPLICIT
    assert item.source_id == "SRC-001"
    assert item.location.section == "Permisos"


def test_inferred_and_ambiguous_items_remain_explicitly_marked():
    normalized = ingest_source(source(), "rules.txt", "texto")
    location = next(iter(__import__("breakers.strike.interpretation", fromlist=["_line_chunks"])._line_chunks(normalized))).location
    inferred = interpreted_item(item_id="I-1", item_type=InterpretationType.BEHAVIOR, statement="Possible behavior", certainty=InterpretationCertainty.INFERRED, source_id="SRC-001", location=location)
    ambiguous = interpreted_item(item_id="I-2", item_type=InterpretationType.CONDITION, statement="Ambiguous condition", certainty=InterpretationCertainty.AMBIGUOUS, source_id="SRC-001", location=location)
    assert inferred.certainty is InterpretationCertainty.INFERRED
    assert ambiguous.certainty is InterpretationCertainty.AMBIGUOUS


def test_missing_expected_behavior_is_not_invented():
    normalized = ingest_source(source(), "api.txt", "La API requiere API Key.")
    result = interpret_deterministically((normalized,))
    assert all(item.type is not InterpretationType.EXPECTED_BEHAVIOR for item in result.items)
    assert all("401" not in item.statement for item in result.items)


def test_contradictions_are_represented_without_resolution():
    from breakers.strike.ingestion import SourceLocation
    a = interpreted_item(item_id="I-A", item_type=InterpretationType.BUSINESS_RULE, statement="Cancelar hasta 24 h antes", certainty=InterpretationCertainty.EXPLICIT, source_id="SRC-A", location=SourceLocation("A"))
    b = interpreted_item(item_id="I-B", item_type=InterpretationType.BUSINESS_RULE, statement="Cancelar hasta 48 h antes", certainty=InterpretationCertainty.EXPLICIT, source_id="SRC-B", location=SourceLocation("B"))
    contradictions = find_contradictions((a, b), (("I-A", "I-B"),))
    assert contradictions[0].item_refs == ("I-A", "I-B")
    assert "24" in a.statement and "48" in b.statement


@pytest.mark.parametrize(("text","expected"), [
    ("Administrador", InterpretationType.ACTOR),
    ("El administrador puede bloquear una cuenta.", InterpretationType.PERMISSION),
    ("El usuario no puede cancelar una compra aprobada.", InterpretationType.RESTRICTION),
    ("El estado cambia a APROBADO.", InterpretationType.TRANSITION),
])
def test_deterministic_explicit_semantics(text, expected):
    result = interpret_deterministically((ingest_source(source(), "rules.txt", text),))
    assert result.items[0].type is expected


def test_stage_two_creates_no_coverage_model_or_test_design():
    result = interpret_deterministically((ingest_source(source(), "rules.txt", "El administrador puede bloquear una cuenta."),))
    assert isinstance(result, InterpretationResult)
    assert not hasattr(result, "coverage_units")
    assert not hasattr(result, "tests")
    assert not hasattr(result, "target_selection")
