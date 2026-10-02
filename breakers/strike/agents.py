from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .evidence_analysis import EvidenceAnalysis, analyze_evidence


class AgentRole(str, Enum):
    EVIDENCE = "EVIDENCE"
    ANALYST = "ANALYST"
    KNOWLEDGE = "KNOWLEDGE"
    COVERAGE = "COVERAGE"
    DESIGNER = "DESIGNER"
    REVIEWER = "REVIEWER"
    REALITY_CHECK = "REALITY_CHECK"


@dataclass(frozen=True)
class AgentTurn:
    cycle: int
    role: AgentRole
    action: str
    facts: tuple[str, ...] = ()
    refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class AgenticAnalysis:
    evidence: EvidenceAnalysis
    turns: tuple[AgentTurn, ...]
    review_required: bool


def run_analysis_cycle(
    definition_texts: tuple[str, ...],
    existing_test_texts: tuple[str, ...] = (),
) -> AgenticAnalysis:
    """Orchestrate STRIKE's pre-coverage reasoning cycle.

    This is intentionally provider-neutral. Agent roles and their evidence boundary
    are now first-class runtime concepts; semantic/LLM providers can implement the
    reasoning behind these roles without changing the rest of STRIKE.
    """
    evidence = analyze_evidence(definition_texts, existing_test_texts)
    turns: list[AgentTurn] = [
        AgentTurn(
            1, AgentRole.EVIDENCE,
            "Build the complete client-evidence context before drawing conclusions.",
            (f"{len(evidence.evidence_texts)} evidence inputs loaded",),
        ),
        AgentTurn(
            1, AgentRole.ANALYST,
            "Interpret only claims supported by client evidence; do not promote external knowledge to requirements.",
        ),
        AgentTurn(
            1, AgentRole.KNOWLEDGE,
            "Retrieve context-relevant QA knowledge as investigative guidance, never as product truth.",
            tuple(match.source.title for match in evidence.knowledge_matches),
            tuple(match.source.id for match in evidence.knowledge_matches),
        ),
        AgentTurn(
            1, AgentRole.REALITY_CHECK,
            "Keep unsupported but relevant possibilities outside the executable STRIKE plan.",
            (f"{len(evidence.outside_evidence_signals)} outside-evidence signals",),
            tuple(item.knowledge_ref for item in evidence.outside_evidence_signals),
        ),
    ]
    return AgenticAnalysis(evidence, tuple(turns), review_required=True)


def review_traceability(
    designed_test_ids: tuple[str, ...],
    links_by_test: dict[str, tuple[str, ...]],
) -> tuple[AgentTurn, ...]:
    unsupported = tuple(test_id for test_id in designed_test_ids if not links_by_test.get(test_id))
    facts = (
        f"{len(designed_test_ids)} designed tests reviewed",
        f"{len(unsupported)} tests without coverage traceability",
    )
    return (
        AgentTurn(
            2,
            AgentRole.REVIEWER,
            "Reject designed tests that cannot be traced to a supported coverage unit.",
            facts,
            unsupported,
        ),
    )
