from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

from .coverage import CoverageModelResult
from .existing_coverage import ExistingCoverageResult, ExistingTestEvidence
from .models import DefinitionGap, Designability, ExistingCoverage, TestCase, TestOrigin
from .target_selection import TargetSelectionResult


class TestDesignDiagnosticType(str, Enum):
    BLOCKED_BY_DEFINITION = "BLOCKED_BY_DEFINITION"
    EXISTING_COVERAGE_NOT_EVALUABLE = "EXISTING_COVERAGE_NOT_EVALUABLE"
    INSUFFICIENT_EXPECTED_BEHAVIOR = "INSUFFICIENT_EXPECTED_BEHAVIOR"


@dataclass(frozen=True)
class TestDesignDiagnostic:
    type: TestDesignDiagnosticType
    statement: str
    coverage_unit_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class TestDesignCoverageLink:
    test_id: str
    coverage_unit_ids: tuple[str, ...]
    existing: bool


@dataclass(frozen=True)
class TestDesignResult:
    existing_tests: tuple[ExistingTestEvidence, ...]
    designed_tests: tuple[TestCase, ...]
    coverage_links: tuple[TestDesignCoverageLink, ...]
    blocked_unit_ids: tuple[str, ...]
    definition_gaps: tuple[DefinitionGap, ...]
    diagnostics: tuple[TestDesignDiagnostic, ...]


def design_tests(
    coverage: CoverageModelResult,
    existing: ExistingCoverageResult,
    target: TargetSelectionResult,
) -> TestDesignResult:
    units = {unit.id: unit for unit in coverage.coverage_units}
    assessments = {item.coverage_unit_id: item for item in existing.assessments}
    mappings_by_unit = {
        unit_id: tuple(mapping for mapping in existing.mappings if mapping.coverage_unit_id == unit_id)
        for unit_id in units
    }
    existing_by_id = {test.internal_id: test for test in existing.existing_tests}

    selected = tuple(target.selected_unit_ids)
    unknown = set(selected) - set(units)
    if unknown:
        raise ValueError(f"Target Selection references unknown CoverageUnit {sorted(unknown)[0]}")

    designed: list[TestCase] = []
    links: list[TestDesignCoverageLink] = []
    blocked: list[str] = []
    diagnostics: list[TestDesignDiagnostic] = []

    for unit_id in selected:
        unit = units[unit_id]
        assessment = assessments.get(unit_id)
        if assessment is None:
            raise ValueError(f"Existing Coverage has no assessment for selected CoverageUnit {unit_id}")

        mapped_ids = tuple(mapping.existing_test_id for mapping in mappings_by_unit[unit_id])
        for test_id in mapped_ids:
            if test_id in existing_by_id:
                links.append(TestDesignCoverageLink(test_id, (unit_id,), True))

        if unit.designability is Designability.BLOCKED_BY_DEFINITION or unit.definition_gap_ref:
            blocked.append(unit_id)
            diagnostics.append(TestDesignDiagnostic(
                TestDesignDiagnosticType.BLOCKED_BY_DEFINITION,
                "Selected coverage need is blocked by its current definition; no test was invented.",
                (unit_id,),
            ))
            continue

        if assessment.status is ExistingCoverage.COVERED:
            continue

        if assessment.status is ExistingCoverage.NOT_EVALUABLE:
            diagnostics.append(TestDesignDiagnostic(
                TestDesignDiagnosticType.EXISTING_COVERAGE_NOT_EVALUABLE,
                "Existing coverage remains NOT_EVALUABLE; Test Design does not reinterpret it as UNCOVERED.",
                (unit_id,),
            ))

        missing = assessment.missing_aspects if assessment.status is ExistingCoverage.PARTIAL else ()
        design = _design_for_unit(unit.id, unit.statement, missing)
        if design is None:
            blocked.append(unit_id)
            diagnostics.append(TestDesignDiagnostic(
                TestDesignDiagnosticType.INSUFFICIENT_EXPECTED_BEHAVIOR,
                "The selected obligation does not provide enough supported expected behavior for a responsible test design.",
                (unit_id,),
            ))
            continue
        designed.append(design)
        links.append(TestDesignCoverageLink(design.id, design.covers, False))

    return TestDesignResult(
        tuple(existing.existing_tests),
        tuple(_deduplicate_designs(designed)),
        tuple(_deduplicate_links(links)),
        tuple(dict.fromkeys(blocked)),
        tuple(coverage.definition_gaps),
        tuple(diagnostics),
    )


def _design_for_unit(unit_id: str, statement: str, missing: tuple[str, ...]) -> TestCase | None:
    normalized = _normalize(statement)
    expected = _supported_expected(statement)
    if not expected:
        return None

    focus = tuple(aspect for aspect in missing if aspect != "expected result")
    description = f"Validar cobertura faltante de {unit_id}: {', '.join(focus)}" if focus else statement.strip()
    preconditions = _supported_preconditions(statement, focus)
    action = _supported_action(statement)
    if not action:
        return None

    identity_material = "|".join((unit_id, _normalize(description), *sorted(_normalize(x) for x in focus)))
    digest = hashlib.sha256(identity_material.encode("utf-8")).hexdigest()[:12].upper()
    return TestCase(
        id=f"STR-{digest}",
        origin=TestOrigin.STRIKE_COMPLEMENTED if focus else TestOrigin.STRIKE_GENERATED,
        description=description,
        preconditions=preconditions,
        steps=(action,),
        expected_result=expected,
        covers=(unit_id,),
    )


def _supported_expected(statement: str) -> str:
    text = statement.strip().rstrip(".")
    normalized = _normalize(text)
    # Restrictions/permissions carry their own expected semantic outcome. Keep
    # the source-backed obligation verbatim instead of inventing protocol/status details.
    if re.search(r"\b(no puede|no debe|prohibido|no se permite|cannot|must not)\b", normalized):
        return text
    if re.search(r"\b(puede|permite|allowed|can|may)\b", normalized):
        return text
    # Explicit transitions are themselves verifiable expected state changes.
    if re.search(r"\b(?:estado|state)\b.*(?:->|→|\ba\b|\bto\b)", text, re.IGNORECASE):
        return text
    # Explicit data/business constraints can be verified exactly as stated.
    if re.search(r"\b(debe|requiere|required|must|maximo|máximo|exactamente|digitos|dígitos|mb|gb)\b", normalized):
        return text
    return ""


def _supported_preconditions(statement: str, focus: tuple[str, ...]) -> tuple[str, ...]:
    values = list(focus)
    normalized = _normalize(statement)
    for state in ("activa", "activo", "aprobada", "aprobado", "pendiente", "bloqueada", "bloqueado", "vencida", "vencido"):
        if re.search(rf"\b{state}\b", normalized) and state not in values:
            values.append(state)
    return tuple(dict.fromkeys(values))


def _supported_action(statement: str) -> str:
    text = statement.strip().rstrip(".")
    normalized = _normalize(text)
    prefix = re.sub(r"^validar\s+que\s+", "", normalized)
    if not prefix:
        return ""
    return text


def _deduplicate_designs(tests: list[TestCase]) -> tuple[TestCase, ...]:
    result: list[TestCase] = []
    seen: set[tuple] = set()
    for test in tests:
        signature = (
            _normalize(test.description),
            tuple(_normalize(x) for x in test.preconditions),
            tuple(_normalize(x) for x in test.steps),
            _normalize(test.expected_result),
        )
        if signature not in seen:
            seen.add(signature)
            result.append(test)
    return tuple(result)


def _deduplicate_links(links: list[TestDesignCoverageLink]) -> tuple[TestDesignCoverageLink, ...]:
    result: list[TestDesignCoverageLink] = []
    seen: set[tuple] = set()
    for link in links:
        key = (link.test_id, link.coverage_unit_ids, link.existing)
        if key not in seen:
            seen.add(key)
            result.append(link)
    return tuple(result)


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()
