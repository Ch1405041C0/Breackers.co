from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

from .ingestion import SourceLocation
from .interpretation import (
    Contradiction,
    InterpretationCertainty,
    InterpretationResult,
    InterpretationType,
    InterpretedItem,
)
from .models import (
    CoverageUnit,
    DefinitionGap,
    Designability,
    ExistingCoverage,
    Importance,
    TargetState,
)


class CoverageDiagnosticType(str, Enum):
    NON_COVERABLE = "NON_COVERABLE"
    AMBIGUOUS_DEFINITION = "AMBIGUOUS_DEFINITION"
    CONTRADICTION = "CONTRADICTION"
    INSUFFICIENT_DEFINITION = "INSUFFICIENT_DEFINITION"


@dataclass(frozen=True)
class CoverageOrigin:
    coverage_unit_id: str
    interpreted_item_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    locations: tuple[SourceLocation, ...]
    certainties: tuple[InterpretationCertainty, ...]


@dataclass(frozen=True)
class CoverageDiagnostic:
    id: str
    type: CoverageDiagnosticType
    statement: str
    interpreted_item_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    locations: tuple[SourceLocation, ...] = ()


@dataclass(frozen=True)
class CoverageModelResult:
    coverage_units: tuple[CoverageUnit, ...]
    definition_gaps: tuple[DefinitionGap, ...]
    traceability: tuple[CoverageOrigin, ...]
    diagnostics: tuple[CoverageDiagnostic, ...]


_COVERABLE_TYPES = {
    InterpretationType.BEHAVIOR,
    InterpretationType.BUSINESS_RULE,
    InterpretationType.TRANSITION,
    InterpretationType.PERMISSION,
    InterpretationType.RESTRICTION,
    InterpretationType.EXPECTED_BEHAVIOR,
    InterpretationType.DATA_CONSTRAINT,
}
_CONTEXT_TYPES = {InterpretationType.ACTOR, InterpretationType.CONDITION}
_IMPORTANCE_RE = re.compile(r"\b(cr[ií]tic[oa]|critical)\b", re.IGNORECASE)


def build_coverage_model(result: InterpretationResult) -> CoverageModelResult:
    by_id = {item.id: item for item in result.items}
    contradicted = {item_id for contradiction in result.contradictions for item_id in contradiction.item_refs}
    units: list[CoverageUnit] = []
    origins: list[CoverageOrigin] = []
    gaps: list[DefinitionGap] = []
    diagnostics: list[CoverageDiagnostic] = []
    dedup: dict[str, int] = {}

    for contradiction in result.contradictions:
        related = tuple(by_id[item_id] for item_id in contradiction.item_refs if item_id in by_id)
        source_refs = _ordered_unique(item.source_id for item in related)
        gap_id = f"GAP-{len(gaps)+1:03d}"
        gaps.append(DefinitionGap(
            gap_id,
            "Contradictory definitions prevent a single expected behavior.",
            source_refs=source_refs,
            open_quality_question="Which conflicting definition should govern the expected behavior?",
        ))
        diagnostics.append(_diagnostic(
            len(diagnostics) + 1,
            CoverageDiagnosticType.CONTRADICTION,
            contradiction.statement,
            related,
        ))

    consumed_context: set[str] = set()
    coverable = [item for item in result.items if item.type in _COVERABLE_TYPES and item.id not in contradicted]
    for item in coverable:
        related = [item]
        for context in result.items:
            if context.id == item.id or context.id in contradicted or context.type not in _CONTEXT_TYPES:
                continue
            if _contextually_related(context, item):
                related.append(context)
                consumed_context.add(context.id)

        statement = _coverage_statement(item, tuple(related))
        key = _conservative_key(item, statement)
        source_refs = _ordered_unique(x.source_id for x in related)
        certainties = tuple(x.certainty for x in related)
        locations = _ordered_locations(related)
        item_ids = _ordered_unique(x.id for x in related)

        if key in dedup:
            index = dedup[key]
            previous = units[index]
            merged_sources = _ordered_unique((*previous.source_refs, *source_refs))
            units[index] = CoverageUnit(
                id=previous.id,
                statement=previous.statement,
                importance=previous.importance,
                existing_coverage=previous.existing_coverage,
                target_state=previous.target_state,
                designability=previous.designability,
                source_refs=merged_sources,
                test_refs=previous.test_refs,
                logical_group_ref=previous.logical_group_ref,
                exclusion=previous.exclusion,
                definition_gap_ref=previous.definition_gap_ref,
            )
            origin = origins[index]
            origins[index] = CoverageOrigin(
                previous.id,
                _ordered_unique((*origin.interpreted_item_ids, *item_ids)),
                _ordered_unique((*origin.source_ids, *source_refs)),
                _ordered_locations_from_values((*origin.locations, *locations)),
                _ordered_unique((*origin.certainties, *certainties)),
            )
            continue

        unit_id = f"UC-{len(units)+1:03d}"
        gap_ref = None
        designability = Designability.DESIGNABLE
        if InterpretationCertainty.AMBIGUOUS in certainties:
            gap_ref = f"GAP-{len(gaps)+1:03d}"
            designability = Designability.BLOCKED_BY_DEFINITION
            gaps.append(DefinitionGap(
                gap_ref,
                "Coverage need is identifiable but its expected behavior is ambiguous.",
                source_refs=source_refs,
                affected_coverage_units=(unit_id,),
                open_quality_question="What is the intended expected behavior?",
            ))
            diagnostics.append(_diagnostic(
                len(diagnostics) + 1,
                CoverageDiagnosticType.AMBIGUOUS_DEFINITION,
                statement,
                tuple(related),
            ))

        unit = CoverageUnit(
            id=unit_id,
            statement=statement,
            importance=_importance(related),
            existing_coverage=ExistingCoverage.NOT_EVALUABLE,
            target_state=TargetState.NOT_SELECTED,
            designability=designability,
            source_refs=source_refs,
            definition_gap_ref=gap_ref,
        )
        dedup[key] = len(units)
        units.append(unit)
        origins.append(CoverageOrigin(unit_id, item_ids, source_refs, locations, certainties))

    for item in result.items:
        if item.id in contradicted:
            continue
        if item.type is InterpretationType.ACTOR and item.id not in consumed_context:
            diagnostics.append(_diagnostic(
                len(diagnostics) + 1,
                CoverageDiagnosticType.NON_COVERABLE,
                "Isolated actor has no testable obligation.",
                (item,),
            ))
        elif item.type not in _COVERABLE_TYPES and item.type not in _CONTEXT_TYPES:
            diagnostics.append(_diagnostic(
                len(diagnostics) + 1,
                CoverageDiagnosticType.NON_COVERABLE,
                "Interpreted item does not independently express a testable obligation.",
                (item,),
            ))

    return CoverageModelResult(tuple(units), tuple(gaps), tuple(origins), tuple(diagnostics))


def _coverage_statement(primary: InterpretedItem, related: tuple[InterpretedItem, ...]) -> str:
    text = primary.statement.strip().rstrip(".")
    contexts = [item.statement.strip().rstrip(".") for item in related if item.id != primary.id]
    if contexts:
        text = " ".join([*contexts, text])
    return f"Validar que {text[0].lower() + text[1:] if text else text}."


def _contextually_related(context: InterpretedItem, primary: InterpretedItem) -> bool:
    if context.source_id != primary.source_id:
        return False
    if context.location.section and primary.location.section:
        return context.location.section == primary.location.section
    if context.location.line_start is not None and primary.location.line_start is not None:
        return abs(context.location.line_start - primary.location.line_start) <= 2
    return context.location.label == primary.location.label


def _conservative_key(item: InterpretedItem, statement: str) -> str:
    normalized = unicodedata.normalize("NFKD", statement.lower())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
    return f"{item.type.value}:{normalized}"


def _importance(items: list[InterpretedItem]) -> Importance:
    if any(_IMPORTANCE_RE.search(item.statement) for item in items):
        return Importance.CRITICAL
    return Importance.NOT_JUSTIFIED


def _diagnostic(index: int, type_: CoverageDiagnosticType, statement: str, items: tuple[InterpretedItem, ...]) -> CoverageDiagnostic:
    return CoverageDiagnostic(
        f"CD-{index:03d}",
        type_,
        statement,
        _ordered_unique(item.id for item in items),
        _ordered_unique(item.source_id for item in items),
        _ordered_locations(items),
    )


def _ordered_unique(values) -> tuple:
    return tuple(dict.fromkeys(values))


def _ordered_locations(items) -> tuple[SourceLocation, ...]:
    return _ordered_locations_from_values(item.location for item in items)


def _ordered_locations_from_values(values) -> tuple[SourceLocation, ...]:
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)
