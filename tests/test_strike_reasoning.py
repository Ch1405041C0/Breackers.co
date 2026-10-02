import pytest

from breakers.strike.knowledge_base import retrieve_knowledge
from breakers.strike.reasoning import (
    AnalystResponse,
    EvidenceRef,
    NoReasoningProvider,
    ReasonedObservation,
    validate_analyst_response,
)


def test_no_provider_never_invents_reasoning():
    provider = NoReasoningProvider()
    response = provider.analyze((EvidenceRef("EVID-001", "login"),), retrieve_knowledge(("login",)))
    assert response.observations == ()
    assert response.outside_evidence == ()
    assert provider.name == "NONE"


def test_supported_observation_requires_real_evidence_reference():
    response = AnalystResponse(observations=(
        ReasonedObservation("OBS-001", "RULE", "Supported claim", ("EVID-999",)),
    ))
    with pytest.raises(ValueError, match="invented evidence reference"):
        validate_analyst_response(response, {"EVID-001"}, {"OWASP-WSTG"})


def test_supported_observation_cannot_exist_without_evidence():
    response = AnalystResponse(observations=(
        ReasonedObservation("OBS-001", "RULE", "Unsupported claim"),
    ))
    with pytest.raises(ValueError, match="requires at least one evidence reference"):
        validate_analyst_response(response, {"EVID-001"}, {"OWASP-WSTG"})


def test_outside_evidence_can_be_knowledge_only_but_reference_must_exist():
    response = AnalystResponse(outside_evidence=(
        ReasonedObservation("OBS-002", "OUTSIDE_EVIDENCE", "Investigate session lifecycle", (), ("OWASP-WSTG",)),
    ))
    assert validate_analyst_response(response, {"EVID-001"}, {"OWASP-WSTG"}) == response
