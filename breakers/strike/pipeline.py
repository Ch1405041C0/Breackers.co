from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .coverage import CoverageModelResult, build_coverage_model
from .agents import AgentTurn, run_analysis_cycle, review_traceability
from .executability import ExecutabilityResult, analyze_executability
from .existing_coverage import ExistingCoverageResult, map_existing_coverage
from .ingestion import NormalizedSource, ingest_source
from .knowledge import KnowledgeFinding
from .evidence_analysis import EvidenceAnalysis, analyze_evidence
from .interpretation import InterpretationResult, interpret_deterministically
from .models import ClientExclusion, CriticalSelectionPolicy, Source
from .target_selection import (
    TargetSelectionDiagnostic,
    TargetSelectionDiagnosticType,
    TargetSelectionResult,
    select_target,
)
from .test_design import TestDesignResult, design_tests


@dataclass(frozen=True)
class StrikeSourceInput:
    source: Source
    filename: str
    content: str


class StrikePipelineStatus(str, Enum):
    COMPLETE = "COMPLETE"
    ACTION_REQUIRED = "ACTION_REQUIRED"


@dataclass(frozen=True)
class StrikeDiagnostic:
    stage: str
    diagnostic: object


@dataclass(frozen=True)
class StrikeResult:
    status: StrikePipelineStatus
    definition_sources: tuple[NormalizedSource, ...]
    existing_test_sources: tuple[NormalizedSource, ...]
    interpretation: InterpretationResult
    coverage: CoverageModelResult
    existing_coverage: ExistingCoverageResult
    target_selection: TargetSelectionResult | None
    test_design: TestDesignResult | None
    executability: ExecutabilityResult | None
    diagnostics: tuple[StrikeDiagnostic, ...]
    knowledge_findings: tuple[KnowledgeFinding, ...] = ()
    evidence_analysis: EvidenceAnalysis | None = None
    agent_turns: tuple[AgentTurn, ...] = ()


def run_strike(
    definition_sources: tuple[StrikeSourceInput, ...],
    *,
    existing_test_sources: tuple[StrikeSourceInput, ...] = (),
    requested_target: int,
    exclusions: tuple[ClientExclusion, ...] = (),
    critical_policy: CriticalSelectionPolicy | None = None,
) -> StrikeResult:
    if not definition_sources:
        raise ValueError("STRIKE requires at least one definition source")

    normalized_definitions = tuple(
        ingest_source(item.source, item.filename, item.content)
        for item in definition_sources
    )
    normalized_existing = tuple(
        ingest_source(item.source, item.filename, item.content)
        for item in existing_test_sources
    )

    if any(source.existing_tests is not None for source in normalized_definitions):
        raise ValueError("existing-test sources must be supplied through existing_test_sources")
    if any(source.existing_tests is None for source in normalized_existing):
        raise ValueError("existing_test_sources must use Source.kind EXISTING_TESTS")

    interpretation = interpret_deterministically(normalized_definitions)
    agentic = run_analysis_cycle(
        tuple(item.content for item in definition_sources),
        tuple(item.content for item in existing_test_sources),
    )
    evidence_analysis = agentic.evidence
    agent_turns = agentic.turns
    knowledge_findings = evidence_analysis.outside_evidence_signals
    coverage = build_coverage_model(interpretation)
    existing = map_existing_coverage(coverage, normalized_existing)

    try:
        target = select_target(
            coverage,
            existing,
            requested_target,
            exclusions,
            critical_policy,
        )
    except ValueError as exc:
        if "critical_policy is required" not in str(exc):
            raise
        diagnostic = TargetSelectionDiagnostic(
            TargetSelectionDiagnosticType.CRITICAL_TARGET_CONFLICT,
            "Critical Coverage Units exceed the requested target; explicit client policy is required.",
            tuple(unit.id for unit in coverage.coverage_units if unit.importance.value == "CRITICAL"),
        )
        diagnostics = _consolidate_diagnostics(
            interpretation,
            coverage,
            existing,
            target_diagnostics=(diagnostic,),
        )
        return StrikeResult(
            StrikePipelineStatus.ACTION_REQUIRED,
            normalized_definitions,
            normalized_existing,
            interpretation,
            coverage,
            existing,
            None,
            None,
            None,
            diagnostics,
            knowledge_findings,
            evidence_analysis,
            agent_turns,
        )

    test_design = design_tests(coverage, existing, target)
    links_by_test: dict[str, tuple[str, ...]] = {
        test.id: tuple(
            unit_id
            for link in test_design.coverage_links
            if link.test_id == test.id
            for unit_id in link.coverage_unit_ids
        )
        for test in test_design.designed_tests
    }
    agent_turns = (*agent_turns, *review_traceability(
        tuple(test.id for test in test_design.designed_tests),
        links_by_test,
    ))
    executability = analyze_executability(test_design, coverage)
    diagnostics = _consolidate_diagnostics(
        interpretation,
        coverage,
        existing,
        target=target,
        test_design=test_design,
        executability=executability,
    )
    return StrikeResult(
        StrikePipelineStatus.COMPLETE,
        normalized_definitions,
        normalized_existing,
        interpretation,
        coverage,
        existing,
        target,
        test_design,
        executability,
        diagnostics,
        knowledge_findings,
        evidence_analysis,
        agent_turns,
    )


def _consolidate_diagnostics(
    interpretation: InterpretationResult,
    coverage: CoverageModelResult,
    existing: ExistingCoverageResult,
    *,
    target: TargetSelectionResult | None = None,
    target_diagnostics: tuple[TargetSelectionDiagnostic, ...] = (),
    test_design: TestDesignResult | None = None,
    executability: ExecutabilityResult | None = None,
) -> tuple[StrikeDiagnostic, ...]:
    result: list[StrikeDiagnostic] = []
    result.extend(StrikeDiagnostic("INTERPRETATION", item) for item in interpretation.contradictions)
    result.extend(StrikeDiagnostic("COVERAGE", item) for item in coverage.diagnostics)
    result.extend(StrikeDiagnostic("EXISTING_COVERAGE", item) for item in existing.diagnostics)
    result.extend(StrikeDiagnostic("TARGET_SELECTION", item) for item in (target.diagnostics if target else target_diagnostics))
    if test_design:
        result.extend(StrikeDiagnostic("TEST_DESIGN", item) for item in test_design.diagnostics)
    if executability:
        result.extend(StrikeDiagnostic("EXECUTABILITY", item) for item in executability.diagnostics)
    return tuple(result)
