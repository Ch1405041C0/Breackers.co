from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .coverage import CoverageModelResult
from .existing_coverage import ExistingCoverageResult
from .models import ClientExclusion, CoverageUnit, CriticalSelectionPolicy, Importance, TargetSelection


class TargetSelectionDiagnosticType(str, Enum):
    EMPTY_COVERAGE_UNIVERSE = "EMPTY_COVERAGE_UNIVERSE"
    CRITICAL_TARGET_CONFLICT = "CRITICAL_TARGET_CONFLICT"


@dataclass(frozen=True)
class TargetSelectionDiagnostic:
    type: TargetSelectionDiagnosticType
    statement: str
    coverage_unit_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class UnitSelectionRationale:
    coverage_unit_id: str
    selected: bool
    reason: str


@dataclass(frozen=True)
class TargetSelectionResult:
    selection: TargetSelection
    universe_unit_ids: tuple[str, ...]
    selected_unit_ids: tuple[str, ...]
    unselected_unit_ids: tuple[str, ...]
    exclusions: tuple[ClientExclusion, ...]
    diagnostics: tuple[TargetSelectionDiagnostic, ...]
    rationale: tuple[UnitSelectionRationale, ...]


def select_target(
    coverage: CoverageModelResult,
    existing_coverage: ExistingCoverageResult,
    requested_target: int,
    exclusions: tuple[ClientExclusion, ...] = (),
    critical_policy: CriticalSelectionPolicy | None = None,
) -> TargetSelectionResult:
    # Reuse the domain validation for the four allowed V1 target values.
    TargetSelection(requested_target, 0)

    units = tuple(coverage.coverage_units)
    universe_ids = tuple(unit.id for unit in units)
    universe_set = set(universe_ids)
    exclusion_by_unit: dict[str, ClientExclusion] = {}
    for exclusion in exclusions:
        if exclusion.coverage_unit_id not in universe_set:
            raise ValueError(f"Exclusion {exclusion.id} references unknown CoverageUnit {exclusion.coverage_unit_id}")
        if exclusion.coverage_unit_id in exclusion_by_unit:
            raise ValueError(f"CoverageUnit {exclusion.coverage_unit_id} has more than one client exclusion")
        exclusion_by_unit[exclusion.coverage_unit_id] = exclusion

    if not units:
        selection = TargetSelection(requested_target, 0, (), tuple(item.id for item in exclusions), critical_policy)
        diagnostic = TargetSelectionDiagnostic(
            TargetSelectionDiagnosticType.EMPTY_COVERAGE_UNIVERSE,
            "Target Selection has no Coverage Units to select.",
        )
        return TargetSelectionResult(selection, (), (), (), exclusions, (diagnostic,), ())

    # Existing Coverage is deliberately not a priority score. Validate that the
    # supplied mapping belongs to this universe, then leave composition to
    # importance, explicit logical groups and stable identity.
    assessment_ids = {item.coverage_unit_id for item in existing_coverage.assessments}
    unknown_assessments = assessment_ids - universe_set
    if unknown_assessments:
        raise ValueError(f"Existing Coverage references unknown CoverageUnit {sorted(unknown_assessments)[0]}")

    eligible = tuple(unit for unit in units if unit.id not in exclusion_by_unit)
    components = _ordered_components(eligible)
    desired_count = math.ceil(len(units) * requested_target / 100)
    critical_ids = {unit.id for unit in eligible if unit.importance is Importance.CRITICAL}
    diagnostics: list[TargetSelectionDiagnostic] = []

    if len(critical_ids) > desired_count:
        diagnostics.append(TargetSelectionDiagnostic(
            TargetSelectionDiagnosticType.CRITICAL_TARGET_CONFLICT,
            "Critical Coverage Units exceed the requested target; the explicit critical policy determines whether scope expands or Critical units remain outside.",
            tuple(sorted(critical_ids)),
        ))
        if critical_policy is None:
            raise ValueError("critical_policy is required when Critical Coverage Units exceed requested target")

    selected: set[str] = set()
    if critical_policy is CriticalSelectionPolicy.INCLUDE_ALL_CRITICAL and len(critical_ids) > desired_count:
        selected.update(critical_ids)
        selected.update(_group_companions(eligible, selected))
    else:
        for component in components:
            if len(selected) >= desired_count:
                break
            selected.update(unit.id for unit in component)

    # A logical group is an explicit semantic unit: never cut it merely to hit
    # arithmetic exactly.
    selected.update(_group_companions(eligible, selected))

    selected_ids = tuple(unit.id for unit in units if unit.id in selected)
    unselected_ids = tuple(unit.id for unit in units if unit.id not in selected)
    effective = round(len(selected_ids) / len(units) * 100)

    rationales: list[UnitSelectionRationale] = []
    for unit in units:
        exclusion = exclusion_by_unit.get(unit.id)
        if exclusion:
            rationales.append(UnitSelectionRationale(unit.id, False, f"explicitly excluded by client: {exclusion.id}"))
        elif unit.id in selected:
            if unit.importance is Importance.CRITICAL:
                reason = "selected by Critical importance"
            elif unit.logical_group_ref and any(
                other.id in selected and other.id != unit.id and other.logical_group_ref == unit.logical_group_ref
                for other in units
            ):
                reason = f"selected to preserve logical group {unit.logical_group_ref}"
            else:
                reason = "selected by deterministic composition to reach requested scope"
            rationales.append(UnitSelectionRationale(unit.id, True, reason))
        elif unit.importance is Importance.CRITICAL and diagnostics:
            rationales.append(UnitSelectionRationale(unit.id, False, "Critical unit left outside by explicit RESPECT_REQUESTED_TARGET policy"))
        else:
            rationales.append(UnitSelectionRationale(unit.id, False, "outside requested scope"))

    selection = TargetSelection(
        requested_target,
        effective,
        selected_ids,
        tuple(item.id for item in exclusions),
        critical_policy,
    )
    return TargetSelectionResult(
        selection,
        universe_ids,
        selected_ids,
        unselected_ids,
        exclusions,
        tuple(diagnostics),
        tuple(rationales),
    )


def _ordered_components(units: tuple[CoverageUnit, ...]) -> tuple[tuple[CoverageUnit, ...], ...]:
    by_group: dict[str, list[CoverageUnit]] = {}
    singles: list[tuple[CoverageUnit, ...]] = []
    for unit in units:
        if unit.logical_group_ref:
            by_group.setdefault(unit.logical_group_ref, []).append(unit)
        else:
            singles.append((unit,))

    components = [*singles, *(tuple(group) for group in by_group.values())]
    return tuple(sorted(components, key=_component_key))


def _component_key(component: tuple[CoverageUnit, ...]) -> tuple[int, str]:
    importance_order = {
        Importance.CRITICAL: 0,
        Importance.RECOMMENDED: 1,
        Importance.COMPLEMENTARY: 2,
        Importance.NOT_JUSTIFIED: 3,
    }
    return min(importance_order[unit.importance] for unit in component), min(unit.id for unit in component)


def _group_companions(units: tuple[CoverageUnit, ...], selected: set[str]) -> set[str]:
    groups = {
        unit.logical_group_ref
        for unit in units
        if unit.id in selected and unit.logical_group_ref is not None
    }
    return {unit.id for unit in units if unit.logical_group_ref in groups}
