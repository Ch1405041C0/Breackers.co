from __future__ import annotations

import json
from urllib import error, request

from .knowledge_base import KnowledgeMatch
from .reasoning import (
    AnalystResponse,
    EvidenceRef,
    ReasonedObservation,
    ReviewResponse,
)


_OBSERVATION_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "kind": {"type": "string"},
        "statement": {"type": "string"},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
        "knowledge_refs": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string"},
    },
    "required": ["id", "kind", "statement", "evidence_refs", "knowledge_refs", "confidence"],
    "additionalProperties": False,
}
_ANALYST_SCHEMA = {
    "type": "object",
    "properties": {
        "observations": {"type": "array", "items": _OBSERVATION_SCHEMA, "maxItems": 20},
        "outside_evidence": {"type": "array", "items": _OBSERVATION_SCHEMA, "maxItems": 12},
    },
    "required": ["observations", "outside_evidence"],
    "additionalProperties": False,
}
_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "accepted_test_ids": {"type": "array", "items": {"type": "string"}},
        "rejected_test_ids": {"type": "array", "items": {"type": "string"}},
        "observations": {"type": "array", "items": _OBSERVATION_SCHEMA, "maxItems": 20},
    },
    "required": ["accepted_test_ids", "rejected_test_ids", "observations"],
    "additionalProperties": False,
}


class OllamaReasoningError(RuntimeError):
    pass


class OllamaReasoningProvider:
    def __init__(
        self,
        model: str = "ornith:9b",
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: int = 120,
        max_output_tokens: int = 1400,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens

    @property
    def name(self) -> str:
        return f"OLLAMA:{self.model}"

    def analyze(
        self,
        evidence: tuple[EvidenceRef, ...],
        knowledge: tuple[KnowledgeMatch, ...],
    ) -> AnalystResponse:
        payload = {
            "evidence": [{"id": item.id, "text": item.text} for item in evidence],
            "knowledge": [
                {
                    "id": match.source.id,
                    "title": match.source.title,
                    "purpose": match.source.purpose,
                    "matched_concepts": list(match.matched_concepts),
                }
                for match in knowledge
            ],
        }
        system = (
            "You are STRIKE ANALYST, a senior QA reasoning agent. "
            "Analyze ALL supplied client evidence before conclusions. "
            "Supported observations MUST cite evidence_refs. "
            "External QA knowledge is investigative guidance only and MUST NEVER become a client requirement. "
            "If a relevant scenario is not supported by client evidence, put it only in outside_evidence, "
            "with knowledge_refs when applicable. Never invent expected results, requirements, IDs or references. "
            "Be concise; prefer high-value observations over exhaustive prose."
        )
        data = self._chat(system, json.dumps(payload, ensure_ascii=False), _ANALYST_SCHEMA)
        return AnalystResponse(
            observations=tuple(_observation(item) for item in data["observations"]),
            outside_evidence=tuple(_observation(item) for item in data["outside_evidence"]),
        )

    def review(
        self,
        evidence: tuple[EvidenceRef, ...],
        designed_tests: tuple[dict, ...],
    ) -> ReviewResponse:
        payload = {
            "evidence": [{"id": item.id, "text": item.text} for item in evidence],
            "designed_tests": list(designed_tests),
        }
        system = (
            "You are STRIKE REVIEWER. Audit every designed test against supplied client evidence. "
            "Accept only tests whose behavior and expected result are supportable from evidence. "
            "Reject tests that invent behavior. Never invent IDs or references. Be concise."
        )
        data = self._chat(system, json.dumps(payload, ensure_ascii=False), _REVIEW_SCHEMA)
        return ReviewResponse(
            accepted_test_ids=tuple(data["accepted_test_ids"]),
            rejected_test_ids=tuple(data["rejected_test_ids"]),
            observations=tuple(_observation(item) for item in data["observations"]),
        )

    def _chat(self, system: str, user: str, schema: dict) -> dict:
        body = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": schema,
            "options": {
                "temperature": 0,
                "num_predict": self.max_output_tokens,
            },
        }, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                envelope = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise OllamaReasoningError(f"Ollama reasoning request failed: {exc}") from exc
        try:
            content = envelope["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise OllamaReasoningError("Ollama returned an invalid structured response") from exc
        return parsed


def _observation(item: dict) -> ReasonedObservation:
    return ReasonedObservation(
        id=str(item["id"]),
        kind=str(item["kind"]),
        statement=str(item["statement"]),
        evidence_refs=tuple(str(value) for value in item["evidence_refs"]),
        knowledge_refs=tuple(str(value) for value in item["knowledge_refs"]),
        confidence=str(item["confidence"]),
    )
