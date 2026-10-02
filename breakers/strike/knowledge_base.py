from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class KnowledgeSource:
    id: str
    title: str
    publisher: str
    url: str
    topics: tuple[str, ...]
    concepts: tuple[str, ...]
    purpose: str


@dataclass(frozen=True)
class KnowledgeMatch:
    source: KnowledgeSource
    score: int
    matched_concepts: tuple[str, ...]


# STRIKE stores a curated map of knowledge, not copyrighted manuals.
# Sources are provenance. Their concepts guide retrieval; they never become
# product requirements without supporting client evidence.
KNOWLEDGE_SOURCES = (
    KnowledgeSource(
        "OWASP-WSTG",
        "Web Security Testing Guide",
        "OWASP",
        "https://owasp.org/www-project-web-security-testing-guide/",
        ("web", "security", "authentication", "authorization", "session", "input"),
        ("login", "authentication", "password", "credential", "session", "logout",
         "authorization", "access control", "input validation", "error handling"),
        "Security test ideas and areas that may deserve investigation.",
    ),
    KnowledgeSource(
        "OWASP-ASVS",
        "Application Security Verification Standard",
        "OWASP",
        "https://owasp.org/www-project-application-security-verification-standard/",
        ("web", "api", "security", "authentication", "authorization", "session"),
        ("authentication", "password", "credential", "session", "authorization",
         "access control", "validation", "api", "token"),
        "Security verification concepts for applications and APIs.",
    ),
    KnowledgeSource(
        "NIST-SSDF-1.1",
        "Secure Software Development Framework (SSDF) Version 1.1",
        "NIST",
        "https://csrc.nist.gov/pubs/sp/800/218/final",
        ("security", "risk", "software development", "requirements"),
        ("security requirement", "risk", "vulnerability", "software", "requirement"),
        "Risk-oriented secure software development context; not a checklist.",
    ),
    KnowledgeSource(
        "ISO-29119-4-2021",
        "ISO/IEC/IEEE 29119-4:2021 Software testing - Test techniques",
        "ISO/IEC/IEEE",
        "https://www.iso.org/standard/79430.html",
        ("testing", "test design", "coverage", "techniques"),
        ("test", "testing", "coverage", "boundary", "decision", "state", "transition",
         "equivalence", "scenario", "condition"),
        "Reference that test design techniques exist and should be selected by context.",
    ),
    KnowledgeSource(
        "SATISFICE-HTSM",
        "Heuristic Test Strategy Model",
        "Satisfice / James Bach",
        "https://www.satisfice.com/download/heuristic-test-strategy-model",
        ("testing", "heuristics", "strategy", "risk", "quality"),
        ("quality", "risk", "test", "strategy", "data", "platform", "operations",
         "function", "interface", "scenario"),
        "Heuristic prompts for exploring relevant quality dimensions.",
    ),
)


def normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def retrieve_knowledge(evidence_texts: tuple[str, ...], *, limit: int = 5) -> tuple[KnowledgeMatch, ...]:
    corpus = f" {normalize(' '.join(evidence_texts))} "
    matches: list[KnowledgeMatch] = []
    for source in KNOWLEDGE_SOURCES:
        found = tuple(
            concept for concept in source.concepts
            if f" {normalize(concept)} " in corpus
        )
        if not found:
            continue
        # Longer concepts are more specific; reward them without pretending
        # this lexical retriever is semantic reasoning.
        score = sum(max(1, len(normalize(concept).split())) for concept in found)
        matches.append(KnowledgeMatch(source, score, found))
    matches.sort(key=lambda item: (-item.score, item.source.id))
    return tuple(matches[:limit])
