from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .knowledge_base import KnowledgeMatch


@dataclass(frozen=True)
class EvidenceRef:
    id: str
    text: str


@dataclass(frozen=True)
class ReasonedObservation:
    id: str
    kind: str
    statement: str
    evidence_refs: tuple[str, ...] = ()
    knowledge_refs: tuple[str, ...] = ()
    confidence: str = "UNSPECIFIED"


@dataclass(frozen=True)
class AnalystResponse:
    observations: tuple[ReasonedObservation, ...] = ()
    outside_evidence: tuple[ReasonedObservation, ...] = ()


@dataclass(frozen=True)
class ReviewResponse:
    accepted_test_ids: tuple[str, ...] = ()
    rejected_test_ids: tuple[str, ...] = ()
    observations: tuple[ReasonedObservation, ...] = ()


class ReasoningProvider(Protocol):
    """Contract for the semantic reasoning engine behind STRIKE agents."""

    @property
    def name(self) -> str: ...

    def analyze(
        self,
        evidence: tuple[EvidenceRef, ...],
        knowledge: tuple[KnowledgeMatch, ...],
    ) -> AnalystResponse: ...

    def review(
        self,
        evidence: tuple[EvidenceRef, ...],
        designed_tests: tuple[dict, ...],
    ) -> ReviewResponse: ...


class NoReasoningProvider:
    """Safe local fallback: never pretends that semantic reasoning happened."""

    name = "NONE"

    def analyze(
        self,
        evidence: tuple[EvidenceRef, ...],
        knowledge: tuple[KnowledgeMatch, ...],
    ) -> AnalystResponse:
        return AnalystResponse()

    def review(
        self,
        evidence: tuple[EvidenceRef, ...],
        designed_tests: tuple[dict, ...],
    ) -> ReviewResponse:
        return ReviewResponse(
            accepted_test_ids=tuple(str(test.get("id", "")) for test in designed_tests if test.get("id")),
        )


def validate_analyst_response(
    response: AnalystResponse,
    evidence_ids: set[str],
    knowledge_ids: set[str],
) -> AnalystResponse:
    for item in (*response.observations, *response.outside_evidence):
        unknown_evidence = set(item.evidence_refs) - evidence_ids
        unknown_knowledge = set(item.knowledge_refs) - knowledge_ids
        if unknown_evidence:
            raise ValueError(f"Reasoning provider invented evidence reference: {sorted(unknown_evidence)[0]}")
        if unknown_knowledge:
            raise ValueError(f"Reasoning provider invented knowledge reference: {sorted(unknown_knowledge)[0]}")
        if item in response.observations and not item.evidence_refs:
            raise ValueError(f"Supported observation {item.id} requires at least one evidence reference")
    return response
