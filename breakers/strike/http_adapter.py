from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from werkzeug.utils import secure_filename

from .ingestion import UnsupportedSourceFormat
from .models import (
    ClientExclusion,
    CriticalSelectionPolicy,
    ExistingCoverage,
    Source,
    TestOrigin,
)
from .pipeline import StrikePipelineStatus, StrikeResult, StrikeSourceInput, run_strike


DEFINITION_EXTENSIONS = {".txt", ".md", ".csv"}
EXISTING_TEST_EXTENSIONS = {".csv"}
TARGETS = {25, 50, 75, 100}


@dataclass(frozen=True)
class StrikeHttpError(Exception):
    status: int
    code: str
    message: str
    field: str | None = None
    filename: str | None = None
    supported_formats: tuple[str, ...] = ()

    def body(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.field:
            error["field"] = self.field
        if self.filename:
            error["filename"] = self.filename
        if self.supported_formats:
            error["supported_formats"] = list(self.supported_formats)
        return {"error": error}


def execute_strike_request(request, *, max_file_bytes: int) -> dict[str, Any]:
    if not request.content_type or not request.content_type.startswith("multipart/form-data"):
        raise StrikeHttpError(400, "INVALID_REQUEST", "STRIKE requires multipart/form-data")

    definitions = _read_uploads(
        request.files.getlist("definition_sources[]"),
        field="definition_sources",
        kind="DEFINITION",
        prefix="DEF",
        allowed=DEFINITION_EXTENSIONS,
        max_file_bytes=max_file_bytes,
        required=True,
    )
    existing = _read_uploads(
        request.files.getlist("existing_test_sources[]"),
        field="existing_test_sources",
        kind="EXISTING_TESTS",
        prefix="TEST",
        allowed=EXISTING_TEST_EXTENSIONS,
        max_file_bytes=max_file_bytes,
        required=False,
    )
    target = _parse_target(request.form.get("requested_target"))
    policy = _parse_policy(request.form.get("critical_policy"))
    exclusions = _parse_exclusions(request.form.get("exclusions", "[]"))

    try:
        result = run_strike(
            definitions,
            existing_test_sources=existing,
            requested_target=target,
            exclusions=exclusions,
            critical_policy=policy,
        )
    except UnsupportedSourceFormat as exc:
        raise StrikeHttpError(415, "UNSUPPORTED_SOURCE_FORMAT", str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        if message.startswith("Exclusion ") or "client exclusion" in message.lower():
            raise StrikeHttpError(400, "INVALID_EXCLUSIONS", message, field="exclusions") from exc
        raise

    dto = strike_result_dto(result)
    if dto["status"] == "ACTION_REQUIRED":
        dto["decision"]["requested_target"] = target
    return dto


def _read_uploads(
    uploads: Iterable[Any],
    *,
    field: str,
    kind: str,
    prefix: str,
    allowed: set[str],
    max_file_bytes: int,
    required: bool,
) -> tuple[StrikeSourceInput, ...]:
    items = list(uploads)
    if required and not items:
        raise StrikeHttpError(400, "INVALID_REQUEST", "At least one definition source is required", field=field)

    result: list[StrikeSourceInput] = []
    seen: set[str] = set()
    for index, upload in enumerate(items, 1):
        original = (upload.filename or "").strip()
        filename = secure_filename(original)
        if not filename:
            raise StrikeHttpError(400, "INVALID_FILENAME", "A valid filename is required", field=field)
        duplicate_key = filename.casefold()
        if duplicate_key in seen:
            raise StrikeHttpError(400, "DUPLICATE_FILENAME", "Duplicate filenames are not allowed within the same source channel", field=field, filename=filename)
        seen.add(duplicate_key)

        suffix = Path(filename).suffix.lower()
        if suffix not in allowed:
            raise StrikeHttpError(
                415,
                "UNSUPPORTED_SOURCE_FORMAT",
                "Unsupported STRIKE source format",
                field=field,
                filename=filename,
                supported_formats=tuple(sorted(allowed)),
            )

        raw = upload.read(max_file_bytes + 1)
        if len(raw) > max_file_bytes:
            raise StrikeHttpError(413, "PAYLOAD_TOO_LARGE", "Uploaded source exceeds the configured per-file limit", field=field, filename=filename)
        if not raw:
            raise StrikeHttpError(400, "EMPTY_SOURCE", "Source content cannot be empty", field=field, filename=filename)
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise StrikeHttpError(400, "INVALID_ENCODING", "STRIKE V1 text sources must use UTF-8 encoding", field=field, filename=filename) from exc
        if not content.strip():
            raise StrikeHttpError(400, "EMPTY_SOURCE", "Source content cannot be empty", field=field, filename=filename)

        source_id = f"{prefix}-{index:03d}"
        source = Source(source_id, kind, filename)
        result.append(StrikeSourceInput(source, filename, content))
    return tuple(result)


def _parse_target(value: str | None) -> int:
    try:
        target = int(value or "")
    except ValueError as exc:
        raise StrikeHttpError(400, "INVALID_TARGET", "requested_target must be one of 25, 50, 75, 100", field="requested_target") from exc
    if target not in TARGETS:
        raise StrikeHttpError(400, "INVALID_TARGET", "requested_target must be one of 25, 50, 75, 100", field="requested_target")
    return target


def _parse_policy(value: str | None) -> CriticalSelectionPolicy | None:
    if value is None or not value.strip():
        return None
    try:
        return CriticalSelectionPolicy(value.strip())
    except ValueError as exc:
        raise StrikeHttpError(400, "INVALID_CRITICAL_POLICY", "critical_policy is not supported", field="critical_policy") from exc


def _parse_exclusions(value: str) -> tuple[ClientExclusion, ...]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise StrikeHttpError(400, "INVALID_EXCLUSIONS", "exclusions must be a JSON array", field="exclusions") from exc
    if not isinstance(payload, list):
        raise StrikeHttpError(400, "INVALID_EXCLUSIONS", "exclusions must be a JSON array", field="exclusions")
    result: list[ClientExclusion] = []
    seen_ids: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            raise StrikeHttpError(400, "INVALID_EXCLUSIONS", "each exclusion must be an object", field="exclusions")
        exclusion_id = str(item.get("id", "")).strip()
        unit_id = str(item.get("coverage_unit_id", "")).strip()
        reason = str(item.get("reason", "")).strip()
        if not exclusion_id or not unit_id or exclusion_id in seen_ids:
            raise StrikeHttpError(400, "INVALID_EXCLUSIONS", "each exclusion requires a unique id and coverage_unit_id", field="exclusions")
        seen_ids.add(exclusion_id)
        result.append(ClientExclusion(exclusion_id, unit_id, reason))
    return tuple(result)


def strike_result_dto(result: StrikeResult) -> dict[str, Any]:
    sources = [
        {"id": item.source_id, "filename": item.filename, "kind": item.kind}
        for item in (*result.definition_sources, *result.existing_test_sources)
    ]
    diagnostics = [_diagnostic_dto(item) for item in result.diagnostics]

    if result.status is StrikePipelineStatus.ACTION_REQUIRED:
        conflict = next(
            (item["diagnostic"] for item in diagnostics if item["stage"] == "TARGET_SELECTION" and item["diagnostic"].get("type") == "CRITICAL_TARGET_CONFLICT"),
            {},
        )
        return {
            "status": "ACTION_REQUIRED",
            "sources": sources,
            "decision": {
                "type": "CRITICAL_TARGET_CONFLICT",
                "requested_target": None,
                "coverage_unit_ids": conflict.get("coverage_unit_ids", []),
                "options": ["INCLUDE_ALL_CRITICAL", "RESPECT_REQUESTED_TARGET"],
            },
            "diagnostics": diagnostics,
        }

    target = result.target_selection
    design = result.test_design
    execution = result.executability
    if target is None or design is None or execution is None:
        raise ValueError("COMPLETE StrikeResult requires target selection, test design and executability")

    assessments = {item.coverage_unit_id: item for item in result.existing_coverage.assessments}
    selected = set(target.selected_unit_ids)
    units = []
    summary = {"covered": 0, "partial": 0, "uncovered": 0, "not_evaluable": 0}
    summary_keys = {
        ExistingCoverage.COVERED: "covered",
        ExistingCoverage.PARTIAL: "partial",
        ExistingCoverage.UNCOVERED: "uncovered",
        ExistingCoverage.NOT_EVALUABLE: "not_evaluable",
    }
    for unit in result.coverage.coverage_units:
        assessment = assessments.get(unit.id)
        status = assessment.status if assessment else unit.existing_coverage
        summary[summary_keys[status]] += 1
        units.append({
            "id": unit.id,
            "statement": unit.statement,
            "importance": unit.importance.value,
            "existing_coverage": status.value,
            "selected": unit.id in selected,
            "designability": unit.designability.value,
            "source_refs": list(unit.source_refs),
            "definition_gap_id": unit.definition_gap_ref,
        })

    execution_tests = {item.id: item for item in execution.tests}
    links_by_test: dict[str, list[str]] = {}
    for link in design.coverage_links:
        links_by_test.setdefault(link.test_id, []).extend(link.coverage_unit_ids)

    tests: list[dict[str, Any]] = []
    for evidence in design.existing_tests:
        linked = list(dict.fromkeys(links_by_test.get(evidence.internal_id, [])))
        if not linked:
            continue
        analyzed = execution_tests.get(evidence.internal_id)
        tests.append({
            "id": evidence.original_id,
            "internal_id": evidence.internal_id,
            "origin": TestOrigin.EXISTING.value,
            "description": evidence.description,
            "preconditions": [evidence.preconditions] if evidence.preconditions else [],
            "steps": [evidence.steps] if evidence.steps else [],
            "expected_result": evidence.expected_result,
            "coverage_unit_ids": linked,
            "executability": analyzed.executability.value if analyzed else None,
        })
    for test in design.designed_tests:
        analyzed = execution_tests.get(test.id, test)
        tests.append({
            "id": test.id,
            "origin": test.origin.value,
            "description": test.description,
            "preconditions": list(test.preconditions),
            "steps": list(test.steps),
            "expected_result": test.expected_result,
            "coverage_unit_ids": list(test.covers),
            "executability": analyzed.executability.value,
        })

    covered_selected = {
        test_id
        for link in design.coverage_links if link.existing
        for unit_id in link.coverage_unit_ids
        for test_id in (link.test_id,)
        if unit_id in selected and assessments.get(unit_id) and assessments[unit_id].status is ExistingCoverage.COVERED
    }
    complemented = [test for test in design.designed_tests if test.origin is TestOrigin.STRIKE_COMPLEMENTED]
    generated = [test for test in design.designed_tests if test.origin is TestOrigin.STRIKE_GENERATED]

    requirement_tests: dict[str, list[str]] = {}
    for trace in execution.traceability:
        requirement_tests.setdefault(trace.requirement_id, []).append(trace.test_id)

    return {
        "status": "COMPLETE",
        "sources": sources,
        "scope": {
            "requested_target": target.selection.requested_target,
            "effective_target": target.selection.effective_target,
            "critical_policy": target.selection.critical_policy.value if target.selection.critical_policy else None,
            "selected_coverage_unit_ids": list(target.selected_unit_ids),
        },
        "coverage": {
            "identified_count": len(result.coverage.coverage_units),
            "selected_count": len(target.selected_unit_ids),
            "units": units,
        },
        "coverage_summary": summary,
        "plan": {
            "existing_reused_count": len(covered_selected),
            "existing_complemented_count": len(complemented),
            "new_designed_count": len(generated),
            "tests": tests,
        },
        "definition_gaps": [
            {
                "id": gap.id,
                "description": gap.description,
                "source_refs": list(gap.source_refs),
                "coverage_unit_ids": list(gap.affected_coverage_units),
            }
            for gap in result.coverage.definition_gaps
        ],
        "execution": {
            "requirements": [
                {
                    "id": requirement.id,
                    "type": requirement.type.value,
                    "description": requirement.description,
                    "test_ids": list(dict.fromkeys(requirement_tests.get(requirement.id, []))),
                }
                for requirement in execution.requirements
            ],
            "dependencies": [
                {
                    "id": dependency.id,
                    "test_id": dependency.test_id,
                    "depends_on_test_id": dependency.depends_on_test_id,
                }
                for dependency in execution.dependencies
            ],
        },
        "traceability": {
            "coverage_to_sources": [
                {"coverage_unit_id": origin.coverage_unit_id, "source_refs": list(origin.source_ids)}
                for origin in result.coverage.traceability
            ],
            "test_to_coverage": [
                {"test_id": test_id, "coverage_unit_ids": list(dict.fromkeys(unit_ids))}
                for test_id, unit_ids in links_by_test.items()
            ],
        },
        "diagnostics": diagnostics,
    }



def _diagnostic_dto(item) -> dict[str, Any]:
    diagnostic = item.diagnostic
    value: dict[str, Any] = {}
    type_ = getattr(diagnostic, "type", None)
    if type_ is not None:
        value["type"] = getattr(type_, "value", str(type_))
    statement = getattr(diagnostic, "statement", None)
    if statement:
        value["statement"] = statement
    for attr in ("coverage_unit_ids", "existing_test_ids", "test_ids", "requirement_ids", "source_ids"):
        refs = getattr(diagnostic, attr, None)
        if refs:
            value[attr] = list(refs)
    return {"stage": item.stage, "diagnostic": value}
