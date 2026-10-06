from breakers.api_errors import api_error


def test_api_error_has_stable_minimum_contract():
    assert api_error("SCAN_NOT_FOUND", "SCAN inexistente") == {
        "error": {"code": "SCAN_NOT_FOUND", "message": "SCAN inexistente"}
    }


def test_api_error_exposes_action_trace_and_details_when_present():
    payload = api_error(
        "SCAN_FAILED",
        "El análisis no pudo completarse",
        action="Reintentá el SCAN",
        trace_id="job-123",
        details={"stage": "scanning"},
    )
    assert payload["error"]["action"] == "Reintentá el SCAN"
    assert payload["error"]["trace_id"] == "job-123"
    assert payload["error"]["details"] == {"stage": "scanning"}
