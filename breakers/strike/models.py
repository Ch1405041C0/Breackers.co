from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Importance(str, Enum):
    CRITICAL = "CRITICAL"
    RECOMMENDED = "RECOMMENDED"
    COMPLEMENTARY = "COMPLEMENTARY"
    NOT_JUSTIFIED = "NOT_JUSTIFIED"


class ExistingCoverage(str, Enum):
    COVERED = "COVERED"
    PARTIAL = "PARTIAL"
    UNCOVERED = "UNCOVERED"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class TargetState(str, Enum):
    SELECTED = "SELECTED"
    NOT_SELECTED = "NOT_SELECTED"
    EXCLUDED_BY_CLIENT = "EXCLUDED_BY_CLIENT"


class Designability(str, Enum):
    DESIGNABLE = "DESIGNABLE"
    BLOCKED_BY_DEFINITION = "BLOCKED_BY_DEFINITION"


class TestOrigin(str, Enum):
    EXISTING = "EXISTING"
    STRIKE_GENERATED = "STRIKE_GENERATED"
    STRIKE_COMPLEMENTED = "STRIKE_COMPLEMENTED"


class Executability(str, Enum):
    EXECUTABLE = "EXECUTABLE"
    BLOCKED = "BLOCKED"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class ExecutionRequirementType(str, Enum):
    RESOURCE = "RESOURCE"
    DATA = "DATA"
    STATE = "STATE"
    ENVIRONMENT = "ENVIRONMENT"
    CREDENTIAL_REQUIREMENT = "CREDENTIAL_REQUIREMENT"
    EXTERNAL_CONDITION = "EXTERNAL_CONDITION"
    HUMAN_ACTION = "HUMAN_ACTION"


class AutomationAssessment(str, Enum):
    STRONG_CANDIDATE = "STRONG_CANDIDATE"
    CONDITIONAL_CANDIDATE = "CONDITIONAL_CANDIDATE"
    MANUAL_INTERVENTION_REQUIRED = "MANUAL_INTERVENTION_REQUIRED"


@dataclass(frozen=True)
class Source:
    id: str
    kind: str
    reference: str = ""


@dataclass(frozen=True)
class ClientExclusion:
    id: str
    coverage_unit_id: str
    reason: str = ""


@dataclass(frozen=True)
class CoverageUnit:
    id: str
    statement: str
    importance: Importance
    existing_coverage: ExistingCoverage
    target_state: TargetState
    designability: Designability
    source_refs: tuple[str, ...] = ()
    test_refs: tuple[str, ...] = ()
    logical_group_ref: str | None = None
    exclusion: str | None = None
    definition_gap_ref: str | None = None


@dataclass(frozen=True)
class DefinitionGap:
    id: str
    description: str
    source_refs: tuple[str, ...] = ()
    affected_coverage_units: tuple[str, ...] = ()
    designability_impact: Designability = Designability.BLOCKED_BY_DEFINITION
    open_quality_question: str | None = None


@dataclass(frozen=True)
class ExecutionRequirement:
    id: str
    type: ExecutionRequirementType
    description: str = ""


@dataclass(frozen=True)
class Dependency:
    id: str
    test_id: str
    depends_on_test_id: str


@dataclass(frozen=True)
class TestCase:
    id: str
    origin: TestOrigin
    description: str
    source_test_id: str | None = None
    preconditions: tuple[str, ...] = ()
    steps: tuple[str, ...] = ()
    expected_result: str = ""
    covers: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    executability: Executability = Executability.NOT_EVALUABLE
    blockers: tuple[str, ...] = ()
    automation_assessment: AutomationAssessment | None = None


@dataclass(frozen=True)
class TargetSelection:
    requested_target: int
    effective_target: int
    selected_coverage_units: tuple[str, ...] = ()
    exclusions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.requested_target not in {25, 50, 75, 100}:
            raise ValueError("requested_target must be one of 25, 50, 75, 100")
        if not 0 <= self.effective_target <= 100:
            raise ValueError("effective_target must be between 0 and 100")


@dataclass(frozen=True)
class TraceabilityLink:
    source_id: str
    coverage_unit_id: str
    test_id: str | None = None


@dataclass
class StrikePlan:
    sources: list[Source] = field(default_factory=list)
    coverage_units: list[CoverageUnit] = field(default_factory=list)
    existing_tests: list[TestCase] = field(default_factory=list)
    designed_tests: list[TestCase] = field(default_factory=list)
    definition_gaps: list[DefinitionGap] = field(default_factory=list)
    execution_requirements: list[ExecutionRequirement] = field(default_factory=list)
    dependencies: list[Dependency] = field(default_factory=list)
    target_selection: TargetSelection | None = None
    exclusions: list[ClientExclusion] = field(default_factory=list)
    traceability: list[TraceabilityLink] = field(default_factory=list)
    deliverable_config: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        source_ids = _unique_ids(self.sources, "Source")
        coverage_ids = _unique_ids(self.coverage_units, "CoverageUnit")
        tests = [*self.existing_tests, *self.designed_tests]
        test_ids = _unique_ids(tests, "TestCase")
        gap_ids = _unique_ids(self.definition_gaps, "DefinitionGap")
        requirement_ids = _unique_ids(self.execution_requirements, "ExecutionRequirement")
        exclusion_ids = _unique_ids(self.exclusions, "ClientExclusion")
        _unique_ids(self.dependencies, "Dependency")

        tests_by_id = {test.id: test for test in tests}
        coverage_by_id = {unit.id: unit for unit in self.coverage_units}
        exclusions_by_id = {item.id: item for item in self.exclusions}

        for unit in self.coverage_units:
            _require_refs(unit.source_refs, source_ids, f"CoverageUnit {unit.id} source")
            _require_refs(unit.test_refs, test_ids, f"CoverageUnit {unit.id} test")
            if unit.definition_gap_ref and unit.definition_gap_ref not in gap_ids:
                raise ValueError(f"CoverageUnit {unit.id} references unknown DefinitionGap {unit.definition_gap_ref}")
            if unit.exclusion:
                if unit.exclusion not in exclusion_ids:
                    raise ValueError(f"CoverageUnit {unit.id} references unknown exclusion {unit.exclusion}")
                exclusion = exclusions_by_id[unit.exclusion]
                if exclusion.coverage_unit_id != unit.id:
                    raise ValueError(f"CoverageUnit {unit.id} exclusion points to another coverage unit")
            if unit.target_state is TargetState.EXCLUDED_BY_CLIENT and not unit.exclusion:
                raise ValueError(f"CoverageUnit {unit.id} is excluded by client without an explicit exclusion")
            if unit.exclusion and unit.target_state is not TargetState.EXCLUDED_BY_CLIENT:
                raise ValueError(f"CoverageUnit {unit.id} has an exclusion but target_state is not EXCLUDED_BY_CLIENT")

        for exclusion in self.exclusions:
            if exclusion.coverage_unit_id not in coverage_ids:
                raise ValueError(f"Exclusion {exclusion.id} references unknown CoverageUnit {exclusion.coverage_unit_id}")
            unit = coverage_by_id[exclusion.coverage_unit_id]
            if unit.exclusion != exclusion.id or unit.target_state is not TargetState.EXCLUDED_BY_CLIENT:
                raise ValueError(f"Exclusion {exclusion.id} is not coherently linked to CoverageUnit {unit.id}")

        for gap in self.definition_gaps:
            _require_refs(gap.source_refs, source_ids, f"DefinitionGap {gap.id} source")
            _require_refs(gap.affected_coverage_units, coverage_ids, f"DefinitionGap {gap.id} coverage unit")
            for unit_id in gap.affected_coverage_units:
                unit = coverage_by_id[unit_id]
                if unit.definition_gap_ref != gap.id:
                    raise ValueError(f"DefinitionGap {gap.id} is not linked back from CoverageUnit {unit_id}")
                if gap.designability_impact is Designability.BLOCKED_BY_DEFINITION and unit.designability is not Designability.BLOCKED_BY_DEFINITION:
                    raise ValueError(f"DefinitionGap {gap.id} blocks designability but CoverageUnit {unit_id} does not")

        for test in tests:
            _require_refs(test.covers, coverage_ids, f"TestCase {test.id} coverage")
            _require_refs(test.requires, requirement_ids, f"TestCase {test.id} requirement")
            _require_refs(test.produces, requirement_ids, f"TestCase {test.id} produced requirement")
            _require_refs(test.depends_on, test_ids, f"TestCase {test.id} dependency")
            for unit_id in test.covers:
                if test.id not in coverage_by_id[unit_id].test_refs:
                    raise ValueError(f"TestCase {test.id} covers {unit_id} but CoverageUnit does not reference the test")
            for unit_id, unit in coverage_by_id.items():
                if test.id in unit.test_refs and unit_id not in test.covers:
                    raise ValueError(f"CoverageUnit {unit_id} references TestCase {test.id} but the test does not cover it")

        for dependency in self.dependencies:
            if dependency.test_id not in test_ids or dependency.depends_on_test_id not in test_ids:
                raise ValueError(f"Dependency {dependency.id} references an unknown TestCase")
            if dependency.depends_on_test_id not in tests_by_id[dependency.test_id].depends_on:
                raise ValueError(f"Dependency {dependency.id} is not represented by TestCase {dependency.test_id}")

        if self.target_selection:
            selected = set(self.target_selection.selected_coverage_units)
            _require_refs(selected, coverage_ids, "TargetSelection selected coverage unit")
            _require_refs(self.target_selection.exclusions, exclusion_ids, "TargetSelection exclusion")
            model_selected = {unit.id for unit in self.coverage_units if unit.target_state is TargetState.SELECTED}
            if selected != model_selected:
                raise ValueError("TargetSelection selected coverage units do not match CoverageUnit target_state")
            model_exclusions = {unit.exclusion for unit in self.coverage_units if unit.exclusion}
            if set(self.target_selection.exclusions) != model_exclusions:
                raise ValueError("TargetSelection exclusions do not match CoverageUnit exclusions")

        for link in self.traceability:
            if link.source_id not in source_ids:
                raise ValueError(f"Traceability references unknown Source {link.source_id}")
            if link.coverage_unit_id not in coverage_ids:
                raise ValueError(f"Traceability references unknown CoverageUnit {link.coverage_unit_id}")
            if link.test_id is not None and link.test_id not in test_ids:
                raise ValueError(f"Traceability references unknown TestCase {link.test_id}")


def _unique_ids(items, label: str) -> set[str]:
    ids = [item.id for item in items]
    if any(not value for value in ids):
        raise ValueError(f"{label} id cannot be empty")
    if len(ids) != len(set(ids)):
        raise ValueError(f"{label} ids must be unique")
    return set(ids)


def _require_refs(refs, valid_ids: set[str], label: str) -> None:
    for ref in refs:
        if ref not in valid_ids:
            raise ValueError(f"{label} references unknown id {ref}")
