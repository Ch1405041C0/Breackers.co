from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from .ingestion import NormalizedSource, SourceLocation


class InterpretationType(str, Enum):
    ACTOR = "ACTOR"
    BEHAVIOR = "BEHAVIOR"
    BUSINESS_RULE = "BUSINESS_RULE"
    CONDITION = "CONDITION"
    STATE = "STATE"
    TRANSITION = "TRANSITION"
    PERMISSION = "PERMISSION"
    RESTRICTION = "RESTRICTION"
    EXPECTED_BEHAVIOR = "EXPECTED_BEHAVIOR"
    DATA_CONSTRAINT = "DATA_CONSTRAINT"
    EXTERNAL_DEPENDENCY = "EXTERNAL_DEPENDENCY"


class InterpretationCertainty(str, Enum):
    EXPLICIT = "EXPLICIT"
    INFERRED = "INFERRED"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True)
class InterpretedItem:
    id: str
    type: InterpretationType
    statement: str
    certainty: InterpretationCertainty
    source_id: str
    location: SourceLocation


@dataclass(frozen=True)
class Contradiction:
    id: str
    item_refs: tuple[str, ...]
    statement: str


@dataclass(frozen=True)
class InterpretationResult:
    source_ids: tuple[str, ...]
    items: tuple[InterpretedItem, ...]
    contradictions: tuple[Contradiction, ...] = ()


def interpret_deterministically(sources: tuple[NormalizedSource, ...]) -> InterpretationResult:
    """Conservative V1 interpreter.

    It recognizes only explicit linguistic patterns with source locations. It is
    deliberately not a coverage generator and does not invent missing outcomes.
    """
    items: list[InterpretedItem] = []
    for source in sources:
        chunks = source.sections or ()
        if not chunks:
            chunks = tuple(_line_chunks(source))
        for chunk in chunks:
            statements = [part.strip() for part in re.split(r"[\n]+|(?<=[.!?])\s+", chunk.content) if part.strip()]
            for statement in statements:
                item_type = _explicit_type(statement)
                if item_type is None:
                    continue
                items.append(InterpretedItem(
                    id=f"INT-{len(items)+1:04d}",
                    type=item_type,
                    statement=statement,
                    certainty=InterpretationCertainty.EXPLICIT,
                    source_id=source.source_id,
                    location=chunk.location,
                ))
    return InterpretationResult(tuple(source.source_id for source in sources), tuple(items))


def interpreted_item(
    *,
    item_id: str,
    item_type: InterpretationType,
    statement: str,
    certainty: InterpretationCertainty,
    source_id: str,
    location: SourceLocation,
) -> InterpretedItem:
    """Boundary for future semantic/model output after parse/validate/normalize."""
    if not statement.strip():
        raise ValueError("interpreted statement cannot be empty")
    return InterpretedItem(item_id, item_type, statement.strip(), certainty, source_id, location)


def find_contradictions(items: tuple[InterpretedItem, ...], pairs: tuple[tuple[str, str], ...]) -> tuple[Contradiction, ...]:
    """Represent externally/deterministically identified contradictions without resolving them."""
    by_id = {item.id: item for item in items}
    result = []
    for index, (left, right) in enumerate(pairs, 1):
        if left not in by_id or right not in by_id:
            raise ValueError("contradiction references unknown interpreted item")
        result.append(Contradiction(f"CON-{index:03d}", (left, right), "Conflicting source statements"))
    return tuple(result)


def _line_chunks(source: NormalizedSource):
    from .ingestion import NormalizedSection
    lines = source.content.splitlines()
    for number, line in enumerate(lines, 1):
        if line.strip():
            yield NormalizedSection("", line, SourceLocation(f"{source.filename} / line {number}", number, number))


def _explicit_type(statement: str) -> InterpretationType | None:
    text = statement.lower()
    if re.search(r"\b(actor|usuario|administrador|cliente|operator|user|admin)\b", text) and len(text.split()) <= 8:
        return InterpretationType.ACTOR
    if re.search(r"\b(puede|can|may|permite|allowed)\b", text):
        return InterpretationType.PERMISSION
    if re.search(r"\b(no puede|must not|prohibido|no se permite|cannot)\b", text):
        return InterpretationType.RESTRICTION
    if re.search(r"\b(estado|state)\b.*\b(a|to|->|→)\b", text):
        return InterpretationType.TRANSITION
    if re.search(r"\b(estado|state)\b", text):
        return InterpretationType.STATE
    if re.search(r"\b(regla|rule|debe|must|required|requiere)\b", text):
        return InterpretationType.BUSINESS_RULE
    return None
