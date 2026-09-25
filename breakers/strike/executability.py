from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, replace
from enum import Enum

from .coverage import CoverageModelResult
from .models import (
    Dependency,
    Executability,
    ExecutionRequirement,
    ExecutionRequirementType,
    TestCase,
)
from .test_design import TestDesignResult


class ExecutabilityDiagnosticType(str, Enum):
    EXTERNAL_REQUIREMENT = "EXTERNAL_REQUIREMENT"
    CYCLIC_DEPENDENCY = "CYCLIC_DEPENDENCY"
    SELF_DEPENDENCY = "SELF_DEPENDENCY"
    BLOCKED_BY_DEFINITION = "BLOCKED_BY_DEFINITION"


@dataclass(frozen=True)
class RequirementTrace:
    requirement_id: str
    test_id: str
    coverage_unit_ids: tuple[str, ...]


@dataclass(frozen=True)
class ExecutabilityDiagnostic:
    type: ExecutabilityDiagnosticType
    statement: str
    test_ids: tuple[str, ...] = ()
    requirement_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExecutabilityResult:
    tests: tuple[TestCase, ...]
    requirements: tuple[ExecutionRequirement, ...]
    dependencies: tuple[Dependency, ...]
    external_requirements: tuple[ExecutionRequirement, ...]
    traceability: tuple[RequirementTrace, ...]
    diagnostics: tuple[ExecutabilityDiagnostic, ...]


def analyze_executability(
    design: TestDesignResult,
    coverage: CoverageModelResult,
) -> ExecutabilityResult:
    units = {unit.id: unit for unit in coverage.coverage_units}
    blocked_units = set(design.blocked_unit_ids)
    diagnostics: list[ExecutabilityDiagnostic] = []
    requirements: dict[tuple[ExecutionRequirementType, str], ExecutionRequirement] = {}
    traces: list[RequirementTrace] = []

    designed = list(design.designed_tests)
    existing = [_existing_as_test(test, design) for test in design.existing_tests]
    source_tests = [*existing, *designed]
    analyzed: list[TestCase] = []

    for test in source_tests:
        if any(unit_id in blocked_units for unit_id in test.covers):
            diagnostics.append(ExecutabilityDiagnostic(
                ExecutabilityDiagnosticType.BLOCKED_BY_DEFINITION,
                "Definition Gap remains unresolved; executability does not compensate for missing functional definition.",
                (test.id,),
            ))
            analyzed.append(replace(test, executability=Executability.NOT_EVALUABLE))
            continue

        extracted = _requirements_for(test)
        requirement_ids: list[str] = []
        for type_, description in extracted:
            key = (type_, _normalize(description))
            requirement = requirements.get(key)
            if requirement is None:
                requirement = ExecutionRequirement(_stable_id("REQ", type_.value, description), type_, description)
                requirements[key] = requirement
            requirement_ids.append(requirement.id)
            traces.append(RequirementTrace(requirement.id, test.id, test.covers))

        analyzed.append(replace(
            test,
            requires=tuple(dict.fromkeys(requirement_ids)),
            executability=Executability.NOT_EVALUABLE,
        ))

    produced_by: dict[str, list[str]] = {}
    updated: list[TestCase] = []
    for test in analyzed:
        produced_ids = []
        for type_, description in _produces_for(test):
            key = (type_, _normalize(description))
            requirement = requirements.get(key)
            if requirement is None:
                requirement = ExecutionRequirement(_stable_id("REQ", type_.value, description), type_, description)
                requirements[key] = requirement
            produced_ids.append(requirement.id)
            produced_by.setdefault(requirement.id, []).append(test.id)
        updated.append(replace(test, produces=tuple(dict.fromkeys(produced_ids))))

    dependencies: list[Dependency] = []
    external_ids: set[str] = set()
    final_tests: list[TestCase] = []
    for test in updated:
        dependency_ids: list[str] = []
        for requirement_id in test.requires:
            producers = [producer for producer in produced_by.get(requirement_id, ()) if producer != test.id]
            if not producers:
                external_ids.add(requirement_id)
                continue
            for producer in producers:
                dependency = Dependency(_stable_id("DEP", test.id, producer, requirement_id), test.id, producer)
                dependencies.append(dependency)
                dependency_ids.append(producer)
        final_tests.append(replace(test, depends_on=tuple(dict.fromkeys(dependency_ids))))

    dependencies = _deduplicate_dependencies(dependencies)
    cycles = _cycles(tuple(final_tests))
    for cycle in cycles:
        diagnostics.append(ExecutabilityDiagnostic(
            ExecutabilityDiagnosticType.CYCLIC_DEPENDENCY,
            "Cyclic operational dependency detected; STRIKE reports it without resolving execution order.",
            cycle,
        ))

    external = tuple(req for req in requirements.values() if req.id in external_ids)
    for req in external:
        diagnostics.append(ExecutabilityDiagnostic(
            ExecutabilityDiagnosticType.EXTERNAL_REQUIREMENT,
            "Requirement has no known producer in this test set; availability has not been verified.",
            requirement_ids=(req.id,),
        ))

    return ExecutabilityResult(
        tuple(final_tests),
        tuple(requirements.values()),
        tuple(dependencies),
        external,
        tuple(_deduplicate_traces(traces)),
        tuple(diagnostics),
    )


def _existing_as_test(evidence, design: TestDesignResult) -> TestCase:
    covers = tuple(
        unit_id
        for link in design.coverage_links
        if link.existing and link.test_id == evidence.internal_id
        for unit_id in link.coverage_unit_ids
    )
    preconditions = (evidence.preconditions,) if evidence.preconditions else ()
    steps = (evidence.steps,) if evidence.steps else ()
    return TestCase(
        id=evidence.internal_id,
        origin=_existing_origin(),
        description=evidence.description,
        source_test_id=evidence.original_id,
        preconditions=preconditions,
        steps=steps,
        expected_result=evidence.expected_result,
        covers=tuple(dict.fromkeys(covers)),
    )


def _existing_origin():
    from .models import TestOrigin
    return TestOrigin.EXISTING


def _requirements_for(test: TestCase) -> tuple[tuple[ExecutionRequirementType, str], ...]:
    values: list[tuple[ExecutionRequirementType, str]] = []
    texts = [*test.preconditions]
    # Existing tests are intentionally conservative: only structured
    # preconditions/data-like content is used, never a vague title alone.
    for text in texts:
        normalized = _normalize(text)
        if not normalized:
            continue
        if re.search(r"\b(api key|apikey|credencial|credential)\b", normalized):
            values.append((ExecutionRequirementType.CREDENTIAL_REQUIREMENT, _credential_need(text)))
        role = re.search(r"\b(administrador|admin|operator|operador)\b", normalized)
        if role:
            values.append((ExecutionRequirementType.RESOURCE, f"actor con rol {role.group(1)}"))
        state = re.search(r"\b(activa|activo|aprobada|aprobado|pendiente|bloqueada|bloqueado|vencida|vencido|pending|approved)\b", normalized)
        if state:
            values.append((ExecutionRequirementType.STATE, _state_need(text, state.group(1))))
        if re.search(r"\b(archivo|file|pdf|csv|imagen|image)\b", normalized):
            values.append((ExecutionRequirementType.DATA, text.strip()))
        elif re.search(r"\b(dni|dato|data|input|\d+\s*(?:mb|gb|digitos|dígitos))\b", normalized):
            values.append((ExecutionRequirementType.DATA, text.strip()))
        if re.search(r"\b(ambiente|environment|staging|qa|dev|prod)\b", normalized):
            values.append((ExecutionRequirementType.ENVIRONMENT, text.strip()))
        if re.search(r"\b(servicio externo|external service)\b", normalized):
            values.append((ExecutionRequirementType.EXTERNAL_CONDITION, text.strip()))
    return _ordered_unique(values)


def _produces_for(test: TestCase) -> tuple[tuple[ExecutionRequirementType, str], ...]:
    expected = test.expected_result.strip()
    normalized = _normalize(expected)
    if not normalized:
        return ()
    produced: list[tuple[ExecutionRequirementType, str]] = []
    # Only explicit reusable states/resources, not arbitrary expected results.
    match = re.search(r"\b(?:queda|resulta|estado)\s+(?:en\s+)?(activa|activo|aprobada|aprobado|pendiente|bloqueada|bloqueado|vencida|vencido|pending|approved)\b", normalized)
    if match:
        produced.append((ExecutionRequirementType.STATE, match.group(1)))
    created = re.search(r"\b(usuario|cuenta|compra|reserva)\s+(cread[oa]|created)\b", normalized)
    if created:
        produced.append((ExecutionRequirementType.RESOURCE, f"{created.group(1)} {created.group(2)}"))
    return tuple(produced)


def _credential_need(text: str) -> str:
    normalized = _normalize(text)
    if "api key" in normalized or "apikey" in normalized:
        return "credencial requerida de tipo API_KEY"
    return "credencial requerida"


def _state_need(text: str, state: str) -> str:
    normalized = _normalize(text)
    for noun in ("compra", "cuenta", "reserva", "usuario"):
        if noun in normalized:
            return f"{noun} en estado {state}"
    return f"estado {state}"


def _stable_id(prefix: str, *parts: str) -> str:
    material = "|".join(_normalize(part) for part in parts)
    return f"{prefix}-{hashlib.sha256(material.encode('utf-8')).hexdigest()[:12].upper()}"


def _deduplicate_dependencies(items: list[Dependency]) -> list[Dependency]:
    result = []
    seen = set()
    for item in items:
        key = (item.test_id, item.depends_on_test_id)
        if item.test_id == item.depends_on_test_id or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _cycles(tests: tuple[TestCase, ...]) -> tuple[tuple[str, ...], ...]:
    graph = {test.id: tuple(test.depends_on) for test in tests}
    found: set[tuple[str, ...]] = set()
    visiting: list[str] = []

    def visit(node: str) -> None:
        if node in visiting:
            cycle = visiting[visiting.index(node):]
            canonical = tuple(sorted(cycle))
            if len(canonical) > 1:
                found.add(canonical)
            return
        visiting.append(node)
        for dep in graph.get(node, ()):
            visit(dep)
        visiting.pop()

    for node in graph:
        visit(node)
    return tuple(sorted(found))


def _deduplicate_traces(items: list[RequirementTrace]) -> list[RequirementTrace]:
    result = []
    seen = set()
    for item in items:
        key = (item.requirement_id, item.test_id, item.coverage_unit_ids)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _ordered_unique(values):
    return tuple(dict.fromkeys(values))


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()
