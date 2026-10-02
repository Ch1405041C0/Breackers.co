from __future__ import annotations

from dataclasses import dataclass

from .knowledge import KnowledgeFinding, analyze_knowledge_gaps
from .knowledge_base import KnowledgeMatch, retrieve_knowledge


@dataclass(frozen=True)
class EvidenceAnalysis:
    evidence_texts: tuple[str, ...]
    knowledge_matches: tuple[KnowledgeMatch, ...]
    outside_evidence_signals: tuple[KnowledgeFinding, ...]


def analyze_evidence(
    definition_texts: tuple[str, ...],
    existing_test_texts: tuple[str, ...] = (),
) -> EvidenceAnalysis:
    """Analyze the whole client evidence universe before coverage/test design.

    V1 retrieval is deliberately lexical and transparent. It is an adapter point:
    a semantic retriever/LLM can replace it without changing the pipeline contract.
    Existing tests participate as evidence, but never silently become requirements.
    """
    evidence = tuple(text for text in (*definition_texts, *existing_test_texts) if text.strip())
    knowledge = retrieve_knowledge(evidence)

    # Transitional provider: legacy heuristics only propose OUTSIDE-EVIDENCE signals.
    # They cannot create CoverageUnits, expected results or tests.
    signals = analyze_knowledge_gaps(evidence)
    allowed_refs = {match.source.id for match in knowledge}
    filtered = tuple(
        signal for signal in signals
        if any(signal.knowledge_ref.startswith(ref) or ref in signal.knowledge_ref for ref in allowed_refs)
        or signal.knowledge_ref.startswith("ISO-IEC-IEEE-29119")
    )
    return EvidenceAnalysis(evidence, knowledge, filtered)
