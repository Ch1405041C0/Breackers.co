from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from .models import ExistingCoverage, Importance, TestOrigin

if TYPE_CHECKING:
    from .pipeline import StrikeResult


class DeliverableMode(str, Enum):
    BREAKERS_RECOMMENDED = "BREAKERS_RECOMMENDED"
    CUSTOM = "CUSTOM"
    CLIENT_TEMPLATE = "CLIENT_TEMPLATE"


class DeliverableFormat(str, Enum):
    XLSX = "XLSX"
    CSV = "CSV"


class DeliverableField(str, Enum):
    TEST_ID = "TEST_ID"
    TEST_DESCRIPTION = "TEST_DESCRIPTION"
    PRECONDITIONS = "PRECONDITIONS"
    STEPS = "STEPS"
    INPUT_DATA = "INPUT_DATA"
    EXPECTED_RESULT = "EXPECTED_RESULT"
    IMPORTANCE = "IMPORTANCE"
    TEST_ORIGIN = "TEST_ORIGIN"
    COVERAGE_UNIT_ID = "COVERAGE_UNIT_ID"
    COVERAGE_STATEMENT = "COVERAGE_STATEMENT"
    EXISTING_COVERAGE = "EXISTING_COVERAGE"
    DEFINITION_GAP = "DEFINITION_GAP"
    EXECUTION_REQUIREMENTS = "EXECUTION_REQUIREMENTS"
    DEPENDENCIES = "DEPENDENCIES"
    SOURCE_REFERENCES = "SOURCE_REFERENCES"
    TARGET_SCOPE = "TARGET_SCOPE"


@dataclass(frozen=True)
class DeliverableColumnConfiguration:
    field: DeliverableField | None
    visible_name: str
    template_column_name: str | None = None


@dataclass(frozen=True)
class DeliverableContentFilter:
    test_origins: tuple[TestOrigin, ...] = ()
    importance: tuple[Importance, ...] = ()
    existing_coverage: tuple[ExistingCoverage, ...] = ()
    coverage_unit_ids: tuple[str, ...] = ()
    include_tests: bool = True
    include_definition_gaps: bool = False
    include_execution_requirements: bool = False


@dataclass(frozen=True)
class DeliverableSectionConfiguration:
    id: str
    visible_name: str
    content_filter: DeliverableContentFilter
    columns: tuple[DeliverableColumnConfiguration, ...]


@dataclass(frozen=True)
class DeliverableConfiguration:
    mode: DeliverableMode
    format: DeliverableFormat
    sections: tuple[DeliverableSectionConfiguration, ...]

    @classmethod
    def breakers_recommended(cls, format: DeliverableFormat = DeliverableFormat.XLSX) -> "DeliverableConfiguration":
        test_columns = (
            DeliverableColumnConfiguration(DeliverableField.TEST_ID, "ID"),
            DeliverableColumnConfiguration(DeliverableField.TEST_DESCRIPTION, "Escenario"),
            DeliverableColumnConfiguration(DeliverableField.PRECONDITIONS, "Precondiciones"),
            DeliverableColumnConfiguration(DeliverableField.STEPS, "Pasos"),
            DeliverableColumnConfiguration(DeliverableField.INPUT_DATA, "Datos"),
            DeliverableColumnConfiguration(DeliverableField.EXPECTED_RESULT, "Resultado esperado"),
            DeliverableColumnConfiguration(DeliverableField.IMPORTANCE, "Importancia"),
            DeliverableColumnConfiguration(DeliverableField.TEST_ORIGIN, "Origen"),
            DeliverableColumnConfiguration(DeliverableField.COVERAGE_UNIT_ID, "Coverage Unit"),
        )
        gap_columns = (
            DeliverableColumnConfiguration(DeliverableField.COVERAGE_UNIT_ID, "Coverage Unit"),
            DeliverableColumnConfiguration(DeliverableField.DEFINITION_GAP, "Definition Gap"),
            DeliverableColumnConfiguration(DeliverableField.SOURCE_REFERENCES, "Fuentes"),
        )
        requirement_columns = (
            DeliverableColumnConfiguration(DeliverableField.TEST_ID, "Test"),
            DeliverableColumnConfiguration(DeliverableField.EXECUTION_REQUIREMENTS, "Requisitos de ejecución"),
            DeliverableColumnConfiguration(DeliverableField.DEPENDENCIES, "Dependencias"),
        )
        return cls(
            DeliverableMode.BREAKERS_RECOMMENDED,
            format,
            (
                DeliverableSectionConfiguration("tests", "Plan de pruebas", DeliverableContentFilter(), test_columns),
                DeliverableSectionConfiguration("gaps", "Definition Gaps", DeliverableContentFilter(include_tests=False, include_definition_gaps=True), gap_columns),
                DeliverableSectionConfiguration("requirements", "Requisitos de ejecución", DeliverableContentFilter(include_tests=False, include_execution_requirements=True), requirement_columns),
            ),
        )


@dataclass(frozen=True)
class DeliverableRow:
    values: tuple[Any, ...]


@dataclass(frozen=True)
class DeliverableSection:
    id: str
    name: str
    columns: tuple[str, ...]
    fields: tuple[DeliverableField | None, ...]
    rows: tuple[DeliverableRow, ...]


@dataclass(frozen=True)
class Deliverable:
    format: DeliverableFormat
    sections: tuple[DeliverableSection, ...]


class DeliverableDecisionRequired(ValueError):
    """The analysis is valid but a client decision is required before final delivery."""


class DeliverableBuilder:
    def build(self, strike_result: "StrikeResult", configuration: DeliverableConfiguration) -> Deliverable:
        if strike_result.status.value != "COMPLETE":
            raise DeliverableDecisionRequired("STRIKE requires a client decision before a final Deliverable can be built")
        if strike_result.target_selection is None or strike_result.test_design is None or strike_result.executability is None:
            raise ValueError("COMPLETE StrikeResult requires target selection, test design and executability")

        sections = tuple(self._build_section(strike_result, section) for section in configuration.sections)
        return Deliverable(configuration.format, sections)

    def _build_section(self, result: "StrikeResult", config: DeliverableSectionConfiguration) -> DeliverableSection:
        rows: list[DeliverableRow] = []
        if config.content_filter.include_tests:
            rows.extend(self._test_rows(result, config))
        if config.content_filter.include_definition_gaps:
            rows.extend(self._gap_rows(result, config))
        if config.content_filter.include_execution_requirements:
            rows.extend(self._requirement_rows(result, config))
        return DeliverableSection(
            config.id,
            config.visible_name,
            tuple(column.visible_name for column in config.columns),
            tuple(column.field for column in config.columns),
            tuple(rows),
        )

    def _test_rows(self, result: "StrikeResult", config: DeliverableSectionConfiguration) -> list[DeliverableRow]:
        units = {unit.id: unit for unit in result.coverage.coverage_units}
        assessments = {item.coverage_unit_id: item for item in result.existing_coverage.assessments}
        existing = {item.internal_id: item for item in result.test_design.existing_tests}
        execution_tests = {item.id: item for item in result.executability.tests}
        links = result.test_design.coverage_links
        rows: list[DeliverableRow] = []

        test_records: list[tuple[Any, tuple[str, ...], Any | None]] = []
        for evidence in result.test_design.existing_tests:
            coverage_ids = tuple(
                unit_id for link in links if link.test_id == evidence.internal_id
                for unit_id in link.coverage_unit_ids
            )
            if coverage_ids:
                test_records.append((evidence, tuple(dict.fromkeys(coverage_ids)), execution_tests.get(evidence.internal_id)))
        for test in result.test_design.designed_tests:
            test_records.append((test, test.covers, execution_tests.get(test.id, test)))

        for test, coverage_ids, executable_test in test_records:
            for unit_id in coverage_ids or ("",):
                unit = units.get(unit_id)
                if not self._matches_filter(config.content_filter, test, unit, assessments.get(unit_id)):
                    continue
                context = _ProjectionContext(test, executable_test, unit, assessments.get(unit_id), result, existing.get(getattr(test, "internal_id", "")))
                rows.append(DeliverableRow(tuple(_project_field(column.field, context) for column in config.columns)))
        return rows

    def _gap_rows(self, result: "StrikeResult", config: DeliverableSectionConfiguration) -> list[DeliverableRow]:
        units = {unit.id: unit for unit in result.coverage.coverage_units}
        rows = []
        for gap in result.coverage.definition_gaps:
            for unit_id in gap.affected_coverage_units or ("",):
                unit = units.get(unit_id)
                context = _ProjectionContext(None, None, unit, None, result, None, gap=gap)
                rows.append(DeliverableRow(tuple(_project_field(column.field, context) for column in config.columns)))
        return rows

    def _requirement_rows(self, result: "StrikeResult", config: DeliverableSectionConfiguration) -> list[DeliverableRow]:
        requirement_by_id = {item.id: item for item in result.executability.requirements}
        rows = []
        for test in result.executability.tests:
            if not test.requires and not test.depends_on:
                continue
            context = _ProjectionContext(test, test, None, None, result, None, requirements=requirement_by_id)
            rows.append(DeliverableRow(tuple(_project_field(column.field, context) for column in config.columns)))
        return rows

    @staticmethod
    def _matches_filter(filter_: DeliverableContentFilter, test: Any, unit: Any, assessment: Any) -> bool:
        origin = getattr(test, "origin", TestOrigin.EXISTING)
        if filter_.test_origins and origin not in filter_.test_origins:
            return False
        if filter_.importance and (unit is None or unit.importance not in filter_.importance):
            return False
        if filter_.existing_coverage and (assessment is None or assessment.status not in filter_.existing_coverage):
            return False
        if filter_.coverage_unit_ids and (unit is None or unit.id not in filter_.coverage_unit_ids):
            return False
        return True


@dataclass(frozen=True)
class _ProjectionContext:
    test: Any
    executable_test: Any
    unit: Any
    assessment: Any
    result: Any
    existing: Any
    gap: Any = None
    requirements: dict[str, Any] | None = None


def _project_field(field: DeliverableField | None, ctx: _ProjectionContext) -> Any:
    if field is None:
        return ""
    test = ctx.test
    unit = ctx.unit
    existing = ctx.existing
    if field is DeliverableField.TEST_ID:
        if existing is not None:
            return existing.original_id
        return getattr(test, "id", getattr(test, "original_id", "")) if test is not None else ""
    if field is DeliverableField.TEST_DESCRIPTION:
        return getattr(test, "description", "") if test is not None else ""
    if field is DeliverableField.PRECONDITIONS:
        value = getattr(test, "preconditions", ()) if test is not None else ()
        return _display(value)
    if field is DeliverableField.STEPS:
        value = getattr(test, "steps", ()) if test is not None else ()
        return _display(value)
    if field is DeliverableField.INPUT_DATA:
        return getattr(existing, "input_data", "") if existing is not None else ""
    if field is DeliverableField.EXPECTED_RESULT:
        return getattr(test, "expected_result", "") if test is not None else ""
    if field is DeliverableField.IMPORTANCE:
        return unit.importance.value if unit is not None else ""
    if field is DeliverableField.TEST_ORIGIN:
        return getattr(getattr(test, "origin", None), "value", "EXISTING" if existing is not None else "")
    if field is DeliverableField.COVERAGE_UNIT_ID:
        return unit.id if unit is not None else ""
    if field is DeliverableField.COVERAGE_STATEMENT:
        return unit.statement if unit is not None else ""
    if field is DeliverableField.EXISTING_COVERAGE:
        return ctx.assessment.status.value if ctx.assessment is not None else ""
    if field is DeliverableField.DEFINITION_GAP:
        return ctx.gap.description if ctx.gap is not None else ""
    if field is DeliverableField.EXECUTION_REQUIREMENTS:
        ids = getattr(ctx.executable_test, "requires", ()) if ctx.executable_test is not None else ()
        lookup = ctx.requirements or {item.id: item for item in ctx.result.executability.requirements}
        return " | ".join(lookup[item].description for item in ids if item in lookup)
    if field is DeliverableField.DEPENDENCIES:
        return " | ".join(getattr(ctx.executable_test, "depends_on", ())) if ctx.executable_test is not None else ""
    if field is DeliverableField.SOURCE_REFERENCES:
        if ctx.gap is not None:
            return " | ".join(ctx.gap.source_refs)
        return " | ".join(unit.source_refs) if unit is not None else ""
    if field is DeliverableField.TARGET_SCOPE:
        selection = ctx.result.target_selection.selection
        return f"{selection.effective_target}% selected scope"
    raise ValueError(f"unsupported DeliverableField: {field}")


def _display(value: Any) -> str:
    if isinstance(value, tuple):
        return " | ".join(str(item) for item in value)
    return str(value or "")
