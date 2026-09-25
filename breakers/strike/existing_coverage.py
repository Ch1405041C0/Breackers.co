from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

from .coverage import CoverageModelResult
from .ingestion import ExistingTestTable, NormalizedSource
from .interpretation import InterpretationCertainty
from .models import CoverageUnit, Designability, ExistingCoverage


class MappingContribution(str, Enum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"


class ExistingCoverageDiagnosticType(str, Enum):
    UNMAPPED_TEST = "UNMAPPED_TEST"
    POSSIBLE_REDUNDANCY = "POSSIBLE_REDUNDANCY"
    AMBIGUOUS_TEST_SCHEMA = "AMBIGUOUS_TEST_SCHEMA"
    BLOCKED_DEFINITION = "BLOCKED_DEFINITION"


@dataclass(frozen=True)
class ExistingTestEvidence:
    internal_id: str
    original_id: str
    source_id: str
    original_row: dict[str, str]
    description: str
    preconditions: str = ""
    steps: str = ""
    expected_result: str = ""
    input_data: str = ""
    story_ref: str = ""
    evaluable: bool = True


@dataclass(frozen=True)
class CoverageMapping:
    coverage_unit_id: str
    existing_test_id: str
    contribution: MappingContribution
    evidence: tuple[str, ...]
    missing_aspects: tuple[str, ...]
    certainty: InterpretationCertainty


@dataclass(frozen=True)
class CoverageAssessment:
    coverage_unit_id: str
    status: ExistingCoverage
    existing_test_ids: tuple[str, ...]
    evidence: tuple[str, ...]
    missing_aspects: tuple[str, ...]


@dataclass(frozen=True)
class ExistingCoverageDiagnostic:
    id: str
    type: ExistingCoverageDiagnosticType
    statement: str
    existing_test_ids: tuple[str, ...] = ()
    coverage_unit_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExistingCoverageResult:
    assessments: tuple[CoverageAssessment, ...]
    mappings: tuple[CoverageMapping, ...]
    existing_tests: tuple[ExistingTestEvidence, ...]
    unmapped_test_ids: tuple[str, ...]
    diagnostics: tuple[ExistingCoverageDiagnostic, ...]


def map_existing_coverage(
    coverage: CoverageModelResult,
    sources: tuple[NormalizedSource, ...],
) -> ExistingCoverageResult:
    tests, diagnostics = _extract_existing_tests(sources)
    mappings: list[CoverageMapping] = []
    assessments: list[CoverageAssessment] = []

    for unit in coverage.coverage_units:
        if unit.designability is Designability.BLOCKED_BY_DEFINITION or unit.definition_gap_ref:
            assessments.append(CoverageAssessment(unit.id, ExistingCoverage.NOT_EVALUABLE, (), (), ("definition is blocked or ambiguous",)))
            diagnostics.append(ExistingCoverageDiagnostic(
                f"ECD-{len(diagnostics)+1:03d}",
                ExistingCoverageDiagnosticType.BLOCKED_DEFINITION,
                "Coverage cannot be declared while the underlying definition is blocked or ambiguous.",
                coverage_unit_ids=(unit.id,),
            ))
            continue

        candidates = [_map_test(unit, test) for test in tests if test.evaluable]
        candidates = [candidate for candidate in candidates if candidate is not None]
        mappings.extend(candidates)

        if not tests or not any(test.evaluable for test in tests):
            assessments.append(CoverageAssessment(unit.id, ExistingCoverage.NOT_EVALUABLE, (), (), ("existing tests are not evaluable",)))
            continue
        if not candidates:
            assessments.append(CoverageAssessment(unit.id, ExistingCoverage.UNCOVERED, (), (), ("no evaluable existing test demonstrates this obligation",)))
            continue

        status, missing = _aggregate_status(unit, candidates)
        assessments.append(CoverageAssessment(
            unit.id,
            status,
            _ordered_unique(mapping.existing_test_id for mapping in candidates),
            _ordered_unique(evidence for mapping in candidates for evidence in mapping.evidence),
            missing,
        ))

    mapped_ids = {mapping.existing_test_id for mapping in mappings}
    unmapped = tuple(test.internal_id for test in tests if test.internal_id not in mapped_ids)
    for test_id in unmapped:
        diagnostics.append(ExistingCoverageDiagnostic(
            f"ECD-{len(diagnostics)+1:03d}",
            ExistingCoverageDiagnosticType.UNMAPPED_TEST,
            "Existing test could not be mapped to the current coverage universe; it is preserved.",
            existing_test_ids=(test_id,),
        ))

    by_signature: dict[tuple[str, ...], list[str]] = {}
    for test in tests:
        linked = tuple(sorted(mapping.coverage_unit_id for mapping in mappings if mapping.existing_test_id == test.internal_id))
        if linked:
            by_signature.setdefault(linked, []).append(test.internal_id)
    for linked, test_ids in by_signature.items():
        if len(test_ids) > 1:
            diagnostics.append(ExistingCoverageDiagnostic(
                f"ECD-{len(diagnostics)+1:03d}",
                ExistingCoverageDiagnosticType.POSSIBLE_REDUNDANCY,
                "Multiple existing tests map to the same coverage obligations; review before any consolidation.",
                tuple(test_ids),
                linked,
            ))

    return ExistingCoverageResult(tuple(assessments), tuple(mappings), tuple(tests), unmapped, tuple(diagnostics))


def _extract_existing_tests(sources: tuple[NormalizedSource, ...]) -> tuple[list[ExistingTestEvidence], list[ExistingCoverageDiagnostic]]:
    tests: list[ExistingTestEvidence] = []
    diagnostics: list[ExistingCoverageDiagnostic] = []
    for source in sources:
        table = source.existing_tests
        if table is None:
            continue
        ambiguous_schema = bool(table.unmapped_columns) or any(value == "AMBIGUOUS" for value in table.mapping_confidence.values())
        reverse = {semantic: column for column, semantic in table.proposed_mapping.items()}
        for row_number, row in enumerate(table.rows, 1):
            original_id = _value(row, reverse.get("id")) or f"ROW-{row_number}"
            description = _value(row, reverse.get("description"))
            preconditions = _value(row, reverse.get("preconditions"))
            steps = _value(row, reverse.get("steps"))
            expected = _value(row, reverse.get("expected_result"))
            input_data = _value(row, reverse.get("input"))
            story = _value(row, reverse.get("story"))
            meaningful = [description, preconditions, steps, expected, input_data]
            evaluable = bool(description and (steps or expected or preconditions or input_data)) and not ambiguous_schema
            internal_id = f"{source.source_id}:{original_id}"
            tests.append(ExistingTestEvidence(
                internal_id, original_id, source.source_id, dict(row), description,
                preconditions, steps, expected, input_data, story, evaluable,
            ))
            if ambiguous_schema:
                diagnostics.append(ExistingCoverageDiagnostic(
                    f"ECD-{len(diagnostics)+1:03d}",
                    ExistingCoverageDiagnosticType.AMBIGUOUS_TEST_SCHEMA,
                    "Existing test schema contains ambiguous/unmapped columns; coverage is not inferred from it.",
                    existing_test_ids=(internal_id,),
                ))
    return tests, diagnostics


def _map_test(unit: CoverageUnit, test: ExistingTestEvidence) -> CoverageMapping | None:
    unit_terms = _meaningful_terms(unit.statement)
    test_parts = {
        "description": test.description,
        "preconditions": test.preconditions,
        "steps": test.steps,
        "expected_result": test.expected_result,
        "input": test.input_data,
        "story": test.story_ref,
    }
    combined = " ".join(value for value in test_parts.values() if value)
    test_terms = _meaningful_terms(combined)
    overlap = unit_terms & test_terms
    if not overlap:
        return None

    anchors = _anchors(unit.statement)
    behavior_anchor = _behavior_phrase(_normalize(unit.statement))
    present = {anchor for anchor in anchors if _contains_phrase(combined, anchor)}
    missing = tuple(anchor for anchor in anchors if anchor not in present)
    evidence = tuple(f"{field}: {value}" for field, value in test_parts.items() if value and (_meaningful_terms(value) & overlap))
    explicit_reference = bool(test.story_ref and _contains_phrase(" ".join(unit.source_refs), test.story_ref))
    anchors_present = bool(present)
    substantial = len(overlap) >= 2
    behavior_present = bool(behavior_anchor and _contains_phrase(combined, behavior_anchor))
    if not ((anchors_present and substantial and behavior_present) or explicit_reference):
        return None

    contribution = MappingContribution.FULL if anchors and not missing and bool(test.expected_result) else MappingContribution.PARTIAL
    certainty = InterpretationCertainty.EXPLICIT if contribution is MappingContribution.FULL else InterpretationCertainty.INFERRED
    if not test.expected_result and "expected result" not in missing:
        missing = (*missing, "expected result")
    return CoverageMapping(unit.id, test.internal_id, contribution, evidence, _ordered_unique(missing), certainty)


def _aggregate_status(unit: CoverageUnit, mappings: list[CoverageMapping]) -> tuple[ExistingCoverage, tuple[str, ...]]:
    if any(mapping.contribution is MappingContribution.FULL for mapping in mappings):
        return ExistingCoverage.COVERED, ()
    anchors = set(_anchors(unit.statement))
    missing_sets = [set(mapping.missing_aspects) for mapping in mappings]
    combined_missing = set.intersection(*missing_sets) if missing_sets else anchors
    covered_anchors = set().union(*(anchors - missing for missing in missing_sets)) if missing_sets else set()
    has_expected = any("expected result" not in mapping.missing_aspects for mapping in mappings)
    semantic_missing = {aspect for aspect in combined_missing if aspect != "expected result"}
    if anchors and anchors.issubset(covered_anchors) and not semantic_missing and has_expected:
        return ExistingCoverage.COVERED, ()
    missing = tuple(sorted(combined_missing))
    return ExistingCoverage.PARTIAL, missing or ("complete evidence is not demonstrated",)


def _anchors(statement: str) -> tuple[str, ...]:
    text = _normalize(statement)
    anchors: list[str] = []
    actor = re.search(r"\b(administrador|admin|usuario|cliente|operator|user)\b", text)
    if actor:
        anchors.append(actor.group(1))
    state = re.search(r"\b(activa|activo|aprobada|aprobado|pendiente|bloqueada|bloqueado|vencida|vencido)\b", text)
    if state:
        anchors.append(state.group(1))
    condition = re.search(r"\b(?:hasta|antes|despues|después|al menos|maximo|maximo de|máximo)\b[^,.]*", statement.lower())
    if condition:
        anchors.append(_normalize(condition.group(0)))
    behavior = _behavior_phrase(text)
    if behavior:
        anchors.append(behavior)
    return _ordered_unique(anchors)


def _behavior_phrase(text: str) -> str:
    stop = {"validar", "que", "el", "la", "un", "una", "puede", "no", "debe", "tener", "al", "menos", "como", "estado"}
    terms = [term for term in text.split() if term not in stop and len(term) > 2]
    return terms[0] if terms else ""


def _meaningful_terms(text: str) -> set[str]:
    stop = {"validar","verificar","que","el","la","los","las","un","una","de","del","a","al","y","o","puede","no","debe","como","para","con","sin","resultado","expected"}
    return {term for term in _normalize(text).split() if len(term) > 2 and term not in stop}


def _contains_phrase(text: str, phrase: str) -> bool:
    return _normalize(phrase) in _normalize(text)


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _value(row: dict[str, str], column: str | None) -> str:
    return row.get(column, "").strip() if column else ""


def _ordered_unique(values) -> tuple:
    return tuple(dict.fromkeys(values))
