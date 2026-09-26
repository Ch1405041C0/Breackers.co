from __future__ import annotations

import csv
import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from xml.etree import ElementTree as ET

from .deliverable import (
    DeliverableColumnConfiguration,
    DeliverableConfiguration,
    DeliverableContentFilter,
    DeliverableField,
    DeliverableFormat,
    DeliverableMode,
    DeliverableSectionConfiguration,
)


class TemplateMappingStatus(str, Enum):
    MATCHED = "MATCHED"
    PROPOSED = "PROPOSED"
    AMBIGUOUS = "AMBIGUOUS"
    UNMAPPED = "UNMAPPED"


@dataclass(frozen=True)
class TemplateColumnMapping:
    original_column: str
    status: TemplateMappingStatus
    mapped_field: DeliverableField | None = None
    candidates: tuple[DeliverableField, ...] = ()


@dataclass(frozen=True)
class TemplateColumn:
    original_name: str
    position: int
    mapping: TemplateColumnMapping


@dataclass(frozen=True)
class TemplateSection:
    original_name: str
    columns: tuple[TemplateColumn, ...]


@dataclass(frozen=True)
class TemplateInspection:
    format: DeliverableFormat
    sections: tuple[TemplateSection, ...]

    def to_configuration(self) -> DeliverableConfiguration:
        sections = tuple(
            DeliverableSectionConfiguration(
                id=f"template-{index}",
                visible_name=section.original_name,
                content_filter=DeliverableContentFilter(),
                columns=tuple(
                    DeliverableColumnConfiguration(
                        column.mapping.mapped_field,
                        column.original_name,
                        template_column_name=column.original_name,
                    )
                    for column in section.columns
                ),
            )
            for index, section in enumerate(self.sections, 1)
        )
        return DeliverableConfiguration(DeliverableMode.CLIENT_TEMPLATE, self.format, sections)


class UnsupportedTemplateFormat(ValueError):
    pass


def inspect_template(filename: str, content: str | bytes) -> TemplateInspection:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        return _inspect_csv(content)
    if suffix == ".xlsx":
        return _inspect_xlsx(content)
    raise UnsupportedTemplateFormat(f"unsupported deliverable template format: {suffix or '<none>'}")


_EXACT = {
    "id": DeliverableField.TEST_ID,
    "descripcion": DeliverableField.TEST_DESCRIPTION,
    "precondiciones": DeliverableField.PRECONDITIONS,
    "pasos": DeliverableField.STEPS,
    "datos": DeliverableField.INPUT_DATA,
    "resultado esperado": DeliverableField.EXPECTED_RESULT,
    "importancia": DeliverableField.IMPORTANCE,
    "origen": DeliverableField.TEST_ORIGIN,
    "coverage unit": DeliverableField.COVERAGE_UNIT_ID,
    "definition gap": DeliverableField.DEFINITION_GAP,
    "requisitos de ejecucion": DeliverableField.EXECUTION_REQUIREMENTS,
    "dependencias": DeliverableField.DEPENDENCIES,
    "fuentes": DeliverableField.SOURCE_REFERENCES,
    "alcance seleccionado": DeliverableField.TARGET_SCOPE,
}

_PROPOSED = {
    "nro": DeliverableField.TEST_ID,
    "numero": DeliverableField.TEST_ID,
    "detalle": DeliverableField.TEST_DESCRIPTION,
    "escenario": DeliverableField.TEST_DESCRIPTION,
    "condicion previa": DeliverableField.PRECONDITIONS,
    "precondition": DeliverableField.PRECONDITIONS,
    "accionar": DeliverableField.STEPS,
    "steps": DeliverableField.STEPS,
    "validacion": DeliverableField.EXPECTED_RESULT,
    "expected result": DeliverableField.EXPECTED_RESULT,
    "prioridad": DeliverableField.IMPORTANCE,
    "source": DeliverableField.SOURCE_REFERENCES,
}

_AMBIGUOUS = {
    "resultado": (DeliverableField.EXPECTED_RESULT, DeliverableField.EXISTING_COVERAGE),
    "estado": (DeliverableField.EXISTING_COVERAGE, DeliverableField.TARGET_SCOPE),
    "cobertura": (DeliverableField.EXISTING_COVERAGE, DeliverableField.TARGET_SCOPE),
}


def map_template_column(name: str) -> TemplateColumnMapping:
    normalized = _normalize(name)
    if normalized in _EXACT:
        field = _EXACT[normalized]
        return TemplateColumnMapping(name, TemplateMappingStatus.MATCHED, field, (field,))
    if normalized in _PROPOSED:
        field = _PROPOSED[normalized]
        return TemplateColumnMapping(name, TemplateMappingStatus.PROPOSED, field, (field,))
    if normalized in _AMBIGUOUS:
        return TemplateColumnMapping(name, TemplateMappingStatus.AMBIGUOUS, None, _AMBIGUOUS[normalized])
    return TemplateColumnMapping(name, TemplateMappingStatus.UNMAPPED)


def _inspect_csv(content: str | bytes) -> TemplateInspection:
    text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
    reader = csv.reader(io.StringIO(text))
    try:
        headers = next(reader)
    except StopIteration as exc:
        raise ValueError("CSV template requires a header row") from exc
    headers = [header.strip() for header in headers]
    if not headers or not any(headers):
        raise ValueError("CSV template requires headers")
    section = TemplateSection(
        "CSV",
        tuple(TemplateColumn(name, index, map_template_column(name)) for index, name in enumerate(headers, 1)),
    )
    return TemplateInspection(DeliverableFormat.CSV, (section,))


def _inspect_xlsx(content: str | bytes) -> TemplateInspection:
    if isinstance(content, str):
        raise TypeError("XLSX template content must be bytes")
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError("invalid XLSX template") from exc

    with archive:
        shared = _shared_strings(archive)
        workbook = _xml(archive, "xl/workbook.xml")
        rels = _xml(archive, "xl/_rels/workbook.xml.rels")
        rel_targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels
            if rel.attrib.get("Id") and rel.attrib.get("Target")
        }
        ns_rel = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        sections: list[TemplateSection] = []
        for sheet in workbook.findall(".//{*}sheet"):
            name = sheet.attrib.get("name", "")
            rel_id = sheet.attrib.get(ns_rel)
            target = rel_targets.get(rel_id or "")
            if not target:
                continue
            path = target.lstrip("/")
            if not path.startswith("xl/"):
                path = "xl/" + path
            sheet_xml = _xml(archive, path)
            headers = _first_row(sheet_xml, shared)
            sections.append(TemplateSection(
                name,
                tuple(TemplateColumn(header, index, map_template_column(header)) for index, header in enumerate(headers, 1)),
            ))
        if not sections:
            raise ValueError("XLSX template contains no readable sheets")
        return TemplateInspection(DeliverableFormat.XLSX, tuple(sections))


def _shared_strings(archive: zipfile.ZipFile) -> tuple[str, ...]:
    try:
        root = _xml(archive, "xl/sharedStrings.xml")
    except KeyError:
        return ()
    return tuple("".join(node.text or "" for node in item.findall(".//{*}t")) for item in root.findall(".//{*}si"))


def _first_row(root: ET.Element, shared: tuple[str, ...]) -> tuple[str, ...]:
    row = root.find(".//{*}sheetData/{*}row")
    if row is None:
        return ()
    values: list[str] = []
    expected_column = 1
    for cell in row.findall("{*}c"):
        reference = cell.attrib.get("r", "")
        column = _column_number(reference)
        while expected_column < column:
            values.append("")
            expected_column += 1
        values.append(_cell_value(cell, shared).strip())
        expected_column += 1
    while values and not values[-1]:
        values.pop()
    return tuple(values)


def _cell_value(cell: ET.Element, shared: tuple[str, ...]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//{*}t"))
    value = cell.find("{*}v")
    raw = value.text if value is not None and value.text is not None else ""
    if cell_type == "s" and raw:
        try:
            return shared[int(raw)]
        except (ValueError, IndexError):
            return ""
    return raw


def _column_number(reference: str) -> int:
    letters = re.match(r"([A-Z]+)", reference.upper())
    if not letters:
        return 1
    result = 0
    for char in letters.group(1):
        result = result * 26 + ord(char) - 64
    return result


def _xml(archive: zipfile.ZipFile, path: str) -> ET.Element:
    return ET.fromstring(archive.read(path))


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text)
