import pytest

from breakers.strike import (
    ClientExclusion,
    CoverageUnit,
    DefinitionGap,
    Dependency,
    Designability,
    Executability,
    ExecutionRequirement,
    ExecutionRequirementType,
    ExistingCoverage,
    Importance,
    Source,
    StrikePlan,
    TargetSelection,
    TargetState,
    TestCase,
    TestOrigin,
    TraceabilityLink,
)


def uc(
    id,
    *,
    importance=Importance.RECOMMENDED,
    existing=ExistingCoverage.UNCOVERED,
    target=TargetState.NOT_SELECTED,
    designability=Designability.DESIGNABLE,
    sources=("SRC-1",),
    tests=(),
    exclusion=None,
    gap=None,
):
    return CoverageUnit(
        id=id,
        statement=f"Coverage {id}",
        importance=importance,
        existing_coverage=existing,
        target_state=target,
        designability=designability,
        source_refs=sources,
        test_refs=tests,
        exclusion=exclusion,
        definition_gap_ref=gap,
    )


def test_coverage_unit_can_exist_without_test():
    plan = StrikePlan(sources=[Source("SRC-1", "requirement")], coverage_units=[uc("UC-1")])
    plan.validate()


def test_coverage_unit_can_reference_multiple_tests():
    tests = [
        TestCase("T-1", TestOrigin.STRIKE_GENERATED, "one", covers=("UC-1",)),
        TestCase("T-2", TestOrigin.STRIKE_GENERATED, "two", covers=("UC-1",)),
    ]
    plan = StrikePlan(
        sources=[Source("SRC-1", "requirement")],
        coverage_units=[uc("UC-1", tests=("T-1", "T-2"))],
        designed_tests=tests,
    )
    plan.validate()


def test_test_can_cover_multiple_coverage_units():
    test = TestCase("T-1", TestOrigin.STRIKE_GENERATED, "shared", covers=("UC-1", "UC-2"))
    plan = StrikePlan(
        sources=[Source("SRC-1", "requirement")],
        coverage_units=[uc("UC-1", tests=("T-1",)), uc("UC-2", tests=("T-1",))],
        designed_tests=[test],
    )
    plan.validate()


def test_existing_coverage_is_independent_from_target_state():
    unit = uc("UC-1", existing=ExistingCoverage.COVERED, target=TargetState.NOT_SELECTED)
    assert unit.existing_coverage is ExistingCoverage.COVERED
    assert unit.target_state is TargetState.NOT_SELECTED


def test_designability_is_independent_from_existing_coverage():
    unit = uc("UC-1", existing=ExistingCoverage.COVERED, designability=Designability.BLOCKED_BY_DEFINITION)
    assert unit.existing_coverage is ExistingCoverage.COVERED
    assert unit.designability is Designability.BLOCKED_BY_DEFINITION


def test_critical_coverage_can_be_excluded_by_client():
    exclusion = ClientExclusion("EX-1", "UC-1")
    unit = uc(
        "UC-1",
        importance=Importance.CRITICAL,
        target=TargetState.EXCLUDED_BY_CLIENT,
        exclusion="EX-1",
    )
    plan = StrikePlan(
        sources=[Source("SRC-1", "requirement")],
        coverage_units=[unit],
        exclusions=[exclusion],
        target_selection=TargetSelection(25, 25, exclusions=("EX-1",)),
    )
    plan.validate()


def test_definition_gap_can_block_designability():
    gap = DefinitionGap(
        "GAP-1",
        "Expected behavior is undefined",
        source_refs=("SRC-1",),
        affected_coverage_units=("UC-1",),
        open_quality_question="What should happen?",
    )
    unit = uc("UC-1", designability=Designability.BLOCKED_BY_DEFINITION, gap="GAP-1")
    plan = StrikePlan(
        sources=[Source("SRC-1", "requirement")],
        coverage_units=[unit],
        definition_gaps=[gap],
    )
    plan.validate()


def test_test_can_require_multiple_execution_requirements():
    requirements = [
        ExecutionRequirement("ADMIN_USER", ExecutionRequirementType.RESOURCE),
        ExecutionRequirement("API_KEY", ExecutionRequirementType.CREDENTIAL_REQUIREMENT),
    ]
    test = TestCase("T-1", TestOrigin.STRIKE_GENERATED, "secured action", requires=("ADMIN_USER", "API_KEY"))
    plan = StrikePlan(execution_requirements=requirements, designed_tests=[test])
    plan.validate()


def test_test_can_produce_state_required_by_another():
    state = ExecutionRequirement("PURCHASE_APPROVED", ExecutionRequirementType.STATE)
    producer = TestCase("T-1", TestOrigin.STRIKE_GENERATED, "approve", produces=("PURCHASE_APPROVED",))
    consumer = TestCase("T-2", TestOrigin.STRIKE_GENERATED, "refund", requires=("PURCHASE_APPROVED",))
    plan = StrikePlan(execution_requirements=[state], designed_tests=[producer, consumer])
    plan.validate()


def test_dependency_between_tests_is_representable():
    first = TestCase("T-1", TestOrigin.STRIKE_GENERATED, "first")
    second = TestCase("T-2", TestOrigin.STRIKE_GENERATED, "second", depends_on=("T-1",))
    dependency = Dependency("DEP-1", test_id="T-2", depends_on_test_id="T-1")
    plan = StrikePlan(designed_tests=[first, second], dependencies=[dependency])
    plan.validate()


@pytest.mark.parametrize("value", [0, 24, 26, 70, 101])
def test_requested_target_rejects_non_v1_values(value):
    with pytest.raises(ValueError, match="requested_target"):
        TargetSelection(value, value)


@pytest.mark.parametrize("value", [25, 50, 75, 100])
def test_requested_target_accepts_v1_values(value):
    assert TargetSelection(value, value).requested_target == value


def test_requested_and_effective_target_can_differ():
    selection = TargetSelection(75, 76)
    assert selection.requested_target == 75
    assert selection.effective_target == 76


def test_existing_test_preserves_source_test_id():
    test = TestCase("T-1", TestOrigin.EXISTING, "imported", source_test_id="CLIENT-TC-847")
    assert test.source_test_id == "CLIENT-TC-847"


def test_credential_requirement_needs_no_secret_value():
    requirement = ExecutionRequirement("API_KEY", ExecutionRequirementType.CREDENTIAL_REQUIREMENT)
    test = TestCase("T-1", TestOrigin.STRIKE_GENERATED, "API test", requires=("API_KEY",))
    plan = StrikePlan(execution_requirements=[requirement], designed_tests=[test])
    plan.validate()
    assert not hasattr(requirement, "value")
    assert not hasattr(requirement, "secret")


def test_invalid_references_are_detected_by_aggregate_validation():
    plan = StrikePlan(
        sources=[Source("SRC-1", "requirement")],
        coverage_units=[uc("UC-1", sources=("MISSING-SOURCE",))],
    )
    with pytest.raises(ValueError, match="unknown id"):
        plan.validate()


def test_duplicate_coverage_and_test_ids_are_rejected():
    plan = StrikePlan(
        coverage_units=[uc("UC-1", sources=()), uc("UC-1", sources=())],
        existing_tests=[TestCase("T-1", TestOrigin.EXISTING, "a")],
        designed_tests=[TestCase("T-1", TestOrigin.STRIKE_GENERATED, "b")],
    )
    with pytest.raises(ValueError, match="CoverageUnit ids must be unique"):
        plan.validate()

    plan = StrikePlan(
        existing_tests=[TestCase("T-1", TestOrigin.EXISTING, "a")],
        designed_tests=[TestCase("T-1", TestOrigin.STRIKE_GENERATED, "b")],
    )
    with pytest.raises(ValueError, match="TestCase ids must be unique"):
        plan.validate()


def test_exclusion_must_match_excluded_target_state():
    exclusion = ClientExclusion("EX-1", "UC-1")
    plan = StrikePlan(
        sources=[Source("SRC-1", "requirement")],
        coverage_units=[uc("UC-1", target=TargetState.SELECTED, exclusion="EX-1")],
        exclusions=[exclusion],
    )
    with pytest.raises(ValueError, match="target_state"):
        plan.validate()


def test_traceability_rejects_unknown_test():
    plan = StrikePlan(
        sources=[Source("SRC-1", "requirement")],
        coverage_units=[uc("UC-1")],
        traceability=[TraceabilityLink("SRC-1", "UC-1", "MISSING")],
    )
    with pytest.raises(ValueError, match="unknown TestCase"):
        plan.validate()


def test_executability_is_on_test_not_coverage_unit():
    test = TestCase("T-1", TestOrigin.STRIKE_GENERATED, "blocked", executability=Executability.BLOCKED)
    unit = uc("UC-1")
    assert test.executability is Executability.BLOCKED
    assert not hasattr(unit, "executability")
