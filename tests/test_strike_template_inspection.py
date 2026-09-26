import io
import zipfile

from breakers.strike.deliverable import DeliverableField, DeliverableMode
from breakers.strike.template_inspection import (
    TemplateMappingStatus,
    inspect_template,
    map_template_column,
)


def xlsx_bytes():
    workbook = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
      xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
      <sheets>
        <sheet name="Funcional" sheetId="1" r:id="rId1"/>
        <sheet name="Regresión" sheetId="2" r:id="rId2"/>
      </sheets>
    </workbook>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="worksheet" Target="worksheets/sheet1.xml"/>
      <Relationship Id="rId2" Type="worksheet" Target="worksheets/sheet2.xml"/>
    </Relationships>"""
    sheet1 = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
      <row r="1">
        <c r="A1" t="inlineStr"><is><t>Nro.</t></is></c>
        <c r="B1" t="inlineStr"><is><t>Detalle</t></is></c>
        <c r="C1" t="inlineStr"><is><t>Responsable QA</t></is></c>
      </row>
    </sheetData></worksheet>"""
    sheet2 = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
      <row r="1">
        <c r="A1" t="inlineStr"><is><t>ID</t></is></c>
        <c r="B1" t="inlineStr"><is><t>Resultado</t></is></c>
      </row>
    </sheetData></worksheet>"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet1)
        archive.writestr("xl/worksheets/sheet2.xml", sheet2)
    return buffer.getvalue()


def test_xlsx_detects_sheets_headers_and_preserves_order():
    inspection = inspect_template("modelo.xlsx", xlsx_bytes())
    assert [section.original_name for section in inspection.sections] == ["Funcional", "Regresión"]
    assert [column.original_name for column in inspection.sections[0].columns] == ["Nro.", "Detalle", "Responsable QA"]
    assert [column.position for column in inspection.sections[0].columns] == [1, 2, 3]


def test_csv_detects_single_table_and_headers():
    inspection = inspect_template("modelo.csv", "Nro.,Detalle,Validación\n1,Login,OK\n")
    assert len(inspection.sections) == 1
    assert inspection.sections[0].original_name == "CSV"
    assert [column.original_name for column in inspection.sections[0].columns] == ["Nro.", "Detalle", "Validación"]


def test_mapping_status_matched():
    mapping = map_template_column("Resultado esperado")
    assert mapping.status is TemplateMappingStatus.MATCHED
    assert mapping.mapped_field is DeliverableField.EXPECTED_RESULT


def test_mapping_status_proposed():
    mapping = map_template_column("Accionar")
    assert mapping.status is TemplateMappingStatus.PROPOSED
    assert mapping.mapped_field is DeliverableField.STEPS


def test_mapping_status_ambiguous_has_candidates_but_no_silent_choice():
    mapping = map_template_column("Estado")
    assert mapping.status is TemplateMappingStatus.AMBIGUOUS
    assert mapping.mapped_field is None
    assert len(mapping.candidates) > 1


def test_mapping_status_unmapped_preserves_unknown_column():
    mapping = map_template_column("Responsable QA")
    assert mapping.status is TemplateMappingStatus.UNMAPPED
    assert mapping.original_column == "Responsable QA"
    assert mapping.mapped_field is None
    assert mapping.candidates == ()


def test_client_template_converges_to_deliverable_configuration():
    inspection = inspect_template("modelo.xlsx", xlsx_bytes())
    config = inspection.to_configuration()
    assert config.mode is DeliverableMode.CLIENT_TEMPLATE
    assert [section.visible_name for section in config.sections] == ["Funcional", "Regresión"]
    assert [column.visible_name for column in config.sections[0].columns] == ["Nro.", "Detalle", "Responsable QA"]
    unknown = config.sections[0].columns[2]
    assert unknown.field is None
    assert unknown.template_column_name == "Responsable QA"


def test_template_inspection_is_separate_from_strike_ingestion_contract():
    inspection = inspect_template("modelo.csv", "ID,Detalle\n1,Login\n")
    assert not hasattr(inspection, "existing_tests")
    assert not hasattr(inspection, "source_id")
    assert inspection.to_configuration().mode is DeliverableMode.CLIENT_TEMPLATE


def test_same_template_inspection_is_deterministic():
    first = inspect_template("modelo.xlsx", xlsx_bytes())
    second = inspect_template("modelo.xlsx", xlsx_bytes())
    assert first == second
