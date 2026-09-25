import pytest

from breakers.strike.coverage import CoverageModelResult
from breakers.strike.existing_coverage import CoverageAssessment, ExistingCoverageResult
from breakers.strike.models import (
    ClientExclusion,
    CoverageUnit,
    CriticalSelectionPolicy,
    Designability,
    ExistingCoverage,
    Importance,
    TargetState,
)
from breakers.strike.target_selection import TargetSelectionDiagnosticType, select_target


def unit(index, importance=Importance.NOT_JUSTIFIED, coverage=ExistingCoverage.NOT_EVALUABLE, group=None, blocked=False):
    return CoverageUnit(
        f"UC-{index:03d}", f"Obligation {index}", importance, coverage, TargetState.NOT_SELECTED,
        Designability.BLOCKED_BY_DEFINITION if blocked else Designability.DESIGNABLE,
        logical_group_ref=group,
        definition_gap_ref=f"GAP-{index:03d}" if blocked else None,
    )


def model(*units):
    return CoverageModelResult(tuple(units), (), (), ())


def existing(*units):
    assessments = tuple(CoverageAssessment(u.id, u.existing_coverage, (), (), ()) for u in units)
    return ExistingCoverageResult(assessments, (), (), (), ())


def select(units, target, **kwargs):
    return select_target(model(*units), existing(*units), target, **kwargs)


@pytest.mark.parametrize("value", [25, 50, 75, 100])
def test_only_v1_requested_targets_are_accepted(value):
    assert select((unit(1),), value).selection.requested_target == value


@pytest.mark.parametrize("value", [0, 32, 63, 82, 101])
def test_other_requested_targets_are_rejected(value):
    with pytest.raises(ValueError):
        select((unit(1),), value)


def test_100_selects_whole_universe_without_exclusions_including_all_states():
    units = (
        unit(1, coverage=ExistingCoverage.COVERED),
        unit(2, coverage=ExistingCoverage.PARTIAL),
        unit(3, coverage=ExistingCoverage.UNCOVERED),
        unit(4, coverage=ExistingCoverage.NOT_EVALUABLE, blocked=True),
    )
    result = select(units, 100)
    assert result.selected_unit_ids == tuple(u.id for u in units)
    assert result.selection.effective_target == 100


def test_target_does_not_create_or_delete_coverage_units():
    units = tuple(unit(i) for i in range(1, 5))
    result = select(units, 50)
    assert result.universe_unit_ids == tuple(u.id for u in units)
    assert len(result.selected_unit_ids) == 2


def test_effective_target_is_based_on_coverage_units_not_tests():
    units = tuple(unit(i) for i in range(1, 4))
    result = select(units, 50)
    assert len(result.selected_unit_ids) == 2
    assert result.selection.effective_target == 67


def test_selection_is_reproducible_and_stable_by_identity():
    units = (unit(3), unit(1), unit(4), unit(2))
    first = select(units, 50)
    second = select(units, 50)
    assert first.selected_unit_ids == second.selected_unit_ids
    assert set(first.selected_unit_ids) == {"UC-001", "UC-002"}


def test_monotonicity_across_all_targets():
    units = tuple(unit(i) for i in range(1, 9))
    selected25 = set(select(units, 25).selected_unit_ids)
    selected50 = set(select(units, 50).selected_unit_ids)
    selected75 = set(select(units, 75).selected_unit_ids)
    selected100 = set(select(units, 100).selected_unit_ids)
    assert selected25 <= selected50 <= selected75 <= selected100


def test_importance_precedes_stable_identity_without_inventing_importance():
    units = (
        unit(1, Importance.NOT_JUSTIFIED),
        unit(2, Importance.COMPLEMENTARY),
        unit(3, Importance.RECOMMENDED),
        unit(4, Importance.CRITICAL),
    )
    result = select(units, 50)
    assert result.selected_unit_ids == ("UC-003", "UC-004")
    assert units[0].importance is Importance.NOT_JUSTIFIED


@pytest.mark.parametrize("status", list(ExistingCoverage))
def test_every_existing_coverage_status_can_be_selected(status):
    units = (unit(1, Importance.CRITICAL, status), unit(2))
    result = select(units, 50)
    assert "UC-001" in result.selected_unit_ids


def test_existing_coverage_does_not_turn_target_into_missing_work_selector():
    units = (
        unit(1, Importance.CRITICAL, ExistingCoverage.COVERED),
        unit(2, Importance.NOT_JUSTIFIED, ExistingCoverage.UNCOVERED),
    )
    assert select(units, 50).selected_unit_ids == ("UC-001",)


def test_manual_exclusion_remains_in_universe_and_effective_denominator():
    units = tuple(unit(i) for i in range(1, 5))
    exclusion = ClientExclusion("EX-1", "UC-004", "client decision")
    result = select(units, 100, exclusions=(exclusion,))
    assert "UC-004" in result.universe_unit_ids
    assert "UC-004" not in result.selected_unit_ids
    assert result.selection.effective_target == 75
    assert result.exclusions == (exclusion,)
    assert result.selection.exclusions == ("EX-1",)
    rationale = next(r for r in result.rationale if r.coverage_unit_id == "UC-004")
    assert "EX-1" in rationale.reason


def test_unknown_exclusion_is_rejected():
    with pytest.raises(ValueError):
        select((unit(1),), 100, exclusions=(ClientExclusion("EX-1", "UC-999", "bad"),))


def test_critical_conflict_requires_explicit_policy():
    units = tuple(unit(i, Importance.CRITICAL if i <= 4 else Importance.NOT_JUSTIFIED) for i in range(1, 11))
    with pytest.raises(ValueError, match="critical_policy"):
        select(units, 25)


def test_include_all_critical_expands_effective_target_and_records_conflict():
    units = tuple(unit(i, Importance.CRITICAL if i <= 4 else Importance.NOT_JUSTIFIED) for i in range(1, 11))
    result = select(units, 25, critical_policy=CriticalSelectionPolicy.INCLUDE_ALL_CRITICAL)
    assert set(result.selected_unit_ids) == {"UC-001", "UC-002", "UC-003", "UC-004"}
    assert result.selection.effective_target == 40
    assert result.selection.critical_policy is CriticalSelectionPolicy.INCLUDE_ALL_CRITICAL
    assert result.diagnostics[0].type is TargetSelectionDiagnosticType.CRITICAL_TARGET_CONFLICT


def test_respect_requested_target_can_leave_critical_out_only_explicitly():
    units = tuple(unit(i, Importance.CRITICAL if i <= 4 else Importance.NOT_JUSTIFIED) for i in range(1, 11))
    result = select(units, 25, critical_policy=CriticalSelectionPolicy.RESPECT_REQUESTED_TARGET)
    assert result.selected_unit_ids == ("UC-001", "UC-002", "UC-003")
    assert "UC-004" in result.unselected_unit_ids
    rationale = next(r for r in result.rationale if r.coverage_unit_id == "UC-004")
    assert "RESPECT_REQUESTED_TARGET" in rationale.reason


def test_explicit_logical_group_is_not_split_and_can_raise_effective_target():
    units = (
        unit(1, Importance.CRITICAL),
        unit(2, Importance.RECOMMENDED, group="APPROVAL"),
        unit(3, Importance.RECOMMENDED, group="APPROVAL"),
        unit(4),
        unit(5),
    )
    result = select(units, 25)
    # First component is Critical; at 50 the explicit group enters as a whole.
    expanded = select(units, 50)
    assert result.selected_unit_ids == ("UC-001", "UC-002", "UC-003")
    assert expanded.selected_unit_ids == ("UC-001", "UC-002", "UC-003")
    assert expanded.selection.effective_target == 60


def test_group_selection_remains_monotonic():
    units = (
        unit(1, group="FLOW"), unit(2, group="FLOW"), unit(3), unit(4), unit(5), unit(6)
    )
    assert set(select(units, 25).selected_unit_ids) <= set(select(units, 50).selected_unit_ids)


def test_blocked_unit_can_be_selected_without_becoming_designable():
    blocked = unit(1, Importance.CRITICAL, blocked=True)
    result = select((blocked, unit(2)), 50)
    assert result.selected_unit_ids == ("UC-001",)
    assert blocked.designability is Designability.BLOCKED_BY_DEFINITION
    assert blocked.definition_gap_ref == "GAP-001"


def test_empty_universe_is_explicit_and_never_fake_100():
    result = select((), 100)
    assert result.selection.effective_target == 0
    assert result.selected_unit_ids == ()
    assert result.diagnostics[0].type is TargetSelectionDiagnosticType.EMPTY_COVERAGE_UNIVERSE


def test_rationale_explains_selected_and_unselected_units():
    units = (unit(1, Importance.CRITICAL), unit(2), unit(3), unit(4))
    result = select(units, 25)
    selected = next(r for r in result.rationale if r.coverage_unit_id == "UC-001")
    unselected = next(r for r in result.rationale if r.coverage_unit_id == "UC-004")
    assert selected.selected and "Critical" in selected.reason
    assert not unselected.selected and unselected.reason == "outside requested scope"


def test_stage_boundary_does_not_create_future_objects_or_mutate_inputs():
    units = (unit(1), unit(2))
    coverage = model(*units)
    mapping = existing(*units)
    result = select_target(coverage, mapping, 50)
    assert coverage.coverage_units == units
    assert mapping.assessments[0].status is ExistingCoverage.NOT_EVALUABLE
    assert not hasattr(result, "designed_tests")
    assert not hasattr(result, "execution_requirements")
    assert not hasattr(result, "dependencies")
    assert not hasattr(result, "executability")
