from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .models import Source


class SourceFormat(str, Enum):
    TEXT = "TEXT"
    MARKDOWN = "MARKDOWN"
    CSV = "CSV"


@dataclass(frozen=True)
class SourceLocation:
    label: str
    line_start: int | None = None
    line_end: int | None = None
    row: int | None = None
    section: str | None = None


@dataclass(frozen=True)
class NormalizedSection:
    heading: str
    content: str
    location: SourceLocation


@dataclass(frozen=True)
class ExistingTestTable:
    detected_columns: tuple[str, ...]
    proposed_mapping: dict[str, str]
    mapping_confidence: dict[str, str]
    unmapped_columns: tuple[str, ...]
    rows: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class NormalizedSource:
    source_id: str
    kind: str
    format: SourceFormat
    filename: str
    content: str
    sections: tuple[NormalizedSection, ...] = ()
    csv_columns: tuple[str, ...] = ()
    csv_rows: tuple[dict[str, str], ...] = ()
    existing_tests: ExistingTestTable | None = None
    metadata: dict[str, str] = field(default_factory=dict)


class UnsupportedSourceFormat(ValueError):
    pass


def ingest_source(source: Source, filename: str, content: str) -> NormalizedSource:
    if not source.id:
        raise ValueError("source id is required")
    if not content or not content.strip():
        raise ValueError("source content cannot be empty")
    fmt = _detect_format(filename)
    if fmt is SourceFormat.TEXT:
        return NormalizedSource(source.id, source.kind, fmt, filename, content)
    if fmt is SourceFormat.MARKDOWN:
        return NormalizedSource(source.id, source.kind, fmt, filename, content, sections=_markdown_sections(content))
    return _ingest_csv(source, filename, content, fmt)


def _detect_format(filename: str) -> SourceFormat:
    suffix = Path(filename).suffix.lower()
    formats = {".txt": SourceFormat.TEXT, ".md": SourceFormat.MARKDOWN, ".csv": SourceFormat.CSV}
    try:
        return formats[suffix]
    except KeyError as exc:
        raise UnsupportedSourceFormat(f"unsupported STRIKE source format: {suffix or '<none>'}") from exc


def _markdown_sections(content: str) -> tuple[NormalizedSection, ...]:
    lines = content.splitlines()
    headings = [(i, re.sub(r"^#{1,6}\s+", "", line).strip()) for i, line in enumerate(lines, 1) if re.match(r"^#{1,6}\s+", line)]
    if not headings:
        return (NormalizedSection("(document)", content, SourceLocation("lines 1-%d" % len(lines), 1, len(lines))),)
    sections = []
    for index, (start, heading) in enumerate(headings):
        end = headings[index + 1][0] - 1 if index + 1 < len(headings) else len(lines)
        body = "\n".join(lines[start:end]).strip()
        sections.append(NormalizedSection(heading, body, SourceLocation(f"{heading} / lines {start}-{end}", start, end, section=heading)))
    return tuple(sections)


def _ingest_csv(source: Source, filename: str, content: str, fmt: SourceFormat) -> NormalizedSource:
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise ValueError("CSV requires a header row")
    columns = tuple(column.strip() for column in reader.fieldnames if column is not None)
    rows = tuple({str(key).strip(): value or "" for key, value in row.items() if key is not None} for row in reader)
    if not columns or not rows:
        raise ValueError("CSV requires headers and at least one data row")
    table = _existing_test_table(columns, rows) if source.kind.upper() == "EXISTING_TESTS" else None
    return NormalizedSource(source.id, source.kind, fmt, filename, content, csv_columns=columns, csv_rows=rows, existing_tests=table)


_MAPPING_ALIASES = {
    "id": {"id", "case", "caso", "test case", "testcase"},
    "description": {"description", "descripcion", "descripción", "scenario", "escenario"},
    "preconditions": {"preconditions", "precondition", "precondiciones"},
    "steps": {"steps", "step", "pasos", "when"},
    "expected_result": {"expected result", "expected_result", "resultado esperado", "salida", "then"},
    "input": {"input", "entrada", "given"},
    "priority": {"priority", "prioridad"},
    "story": {"story", "historia"},
}


def _existing_test_table(columns: tuple[str, ...], rows: tuple[dict[str, str], ...]) -> ExistingTestTable:
    proposed, confidence, unmapped = {}, {}, []
    for column in columns:
        normalized = re.sub(r"\s+", " ", column.strip().lower())
        matches = [semantic for semantic, aliases in _MAPPING_ALIASES.items() if normalized in aliases]
        if len(matches) == 1:
            proposed[column] = matches[0]
            confidence[column] = "DETERMINISTIC"
        else:
            unmapped.append(column)
            confidence[column] = "AMBIGUOUS"
    return ExistingTestTable(columns, proposed, confidence, tuple(unmapped), rows)
