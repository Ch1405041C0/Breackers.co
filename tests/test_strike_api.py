import io
import json

import pytest

import app as breakers_app


@pytest.fixture()
def client():
    breakers_app.app.config.update(TESTING=True, STRIKE_MAX_FILE_BYTES=1024 * 1024)
    return breakers_app.app.test_client()


def upload(name, content):
    if isinstance(content, str):
        content = content.encode("utf-8")
    return io.BytesIO(content), name


def post_strike(client, definitions, *, existing=(), target=100, policy=None, exclusions=None):
    data = {
        "definition_sources[]": [upload(name, content) for name, content in definitions],
        "requested_target": str(target),
        "exclusions": json.dumps(exclusions or []),
    }
    if existing:
        data["existing_test_sources[]"] = [upload(name, content) for name, content in existing]
    if policy:
        data["critical_policy"] = policy
    return client.post("/api/strike", data=data, content_type="multipart/form-data")


def simple_definition(index=1):
    return f"r{index}.txt", f"El usuario puede cancelar la reserva {index}."


def critical_definitions():
    return [
        *((f"c{i}.txt", f"Regla crítica: el usuario puede cancelar reserva {i}.") for i in range(1, 5)),
        *((f"n{i}.txt", f"El usuario puede consultar reserva {i}.") for i in range(1, 7)),
    ]


def test_definitions_only_returns_complete(client):
    response = post_strike(client, [simple_definition()])
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "COMPLETE"
    assert body["coverage"]["identified_count"] >= 1
    assert body["scope"]["requested_target"] == 100


def test_definitions_and_existing_csv_are_separate(client):
    csv = "ID,Description,Preconditions,Steps,Expected Result\nTC-1,Cancelar reserva,reserva activa,cancelar reserva,reserva cancelada\n"
    response = post_strike(client, [simple_definition()], existing=[("existing.csv", csv)])
    assert response.status_code == 200
    body = response.get_json()
    assert [item["kind"] for item in body["sources"]] == ["DEFINITION", "EXISTING_TESTS"]
    assert any(test["origin"] == "EXISTING" for test in body["plan"]["tests"])


def test_multiple_definitions_keep_server_source_ids(client):
    response = post_strike(client, [simple_definition(1), simple_definition(2)])
    body = response.get_json()
    assert [item["id"] for item in body["sources"]] == ["DEF-001", "DEF-002"]


@pytest.mark.parametrize("target", (25, 50, 75, 100))
def test_supported_targets(client, target):
    definitions = [simple_definition(i) for i in range(1, 5)]
    body = post_strike(client, definitions, target=target).get_json()
    assert body["status"] == "COMPLETE"
    assert body["scope"]["requested_target"] == target


def test_critical_conflict_is_action_required_200(client):
    response = post_strike(client, critical_definitions(), target=25)
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ACTION_REQUIRED"
    assert body["decision"]["type"] == "CRITICAL_TARGET_CONFLICT"
    assert body["decision"]["requested_target"] == 25
    assert body["decision"]["options"] == ["INCLUDE_ALL_CRITICAL", "RESPECT_REQUESTED_TARGET"]
    assert "scope" not in body and "plan" not in body and "execution" not in body


@pytest.mark.parametrize("policy", ("INCLUDE_ALL_CRITICAL", "RESPECT_REQUESTED_TARGET"))
def test_critical_conflict_rerun_completes_with_policy(client, policy):
    response = post_strike(client, critical_definitions(), target=25, policy=policy)
    body = response.get_json()
    assert response.status_code == 200
    assert body["status"] == "COMPLETE"
    assert body["scope"]["critical_policy"] == policy


def test_identical_requests_have_deterministic_dto(client):
    definitions = [simple_definition(1), simple_definition(2)]
    first = post_strike(client, definitions, target=100).get_json()
    second = post_strike(client, definitions, target=100).get_json()
    assert first == second


@pytest.mark.parametrize(
    "channel,name",
    (("definition", "requirements.xlsx"), ("existing", "tests.xlsx"), ("existing", "tests.txt"), ("existing", "tests.md")),
)
def test_unsupported_source_formats_return_415(client, channel, name):
    if channel == "definition":
        response = post_strike(client, [(name, "content")])
    else:
        response = post_strike(client, [simple_definition()], existing=[(name, "content")])
    assert response.status_code == 415
    assert response.get_json()["error"]["code"] == "UNSUPPORTED_SOURCE_FORMAT"


def test_empty_source_returns_400(client):
    response = post_strike(client, [("empty.txt", "")])
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "EMPTY_SOURCE"


def test_invalid_encoding_returns_400(client):
    response = post_strike(client, [("bad.txt", b"\xff\xfe\xfa")])
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_ENCODING"


def test_invalid_target_returns_400(client):
    response = post_strike(client, [simple_definition()], target=30)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_TARGET"


def test_invalid_policy_returns_400(client):
    response = post_strike(client, [simple_definition()], policy="AUTOMATIC")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_CRITICAL_POLICY"


def test_duplicate_filename_within_channel_returns_400(client):
    response = post_strike(client, [("same.txt", "El usuario puede cancelar."), ("same.txt", "El usuario puede consultar.")])
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "DUPLICATE_FILENAME"


def test_valid_exclusion_is_reflected_in_complete_dto(client):
    exclusions = [{"id": "EX-1", "coverage_unit_id": "UC-002", "reason": "Fuera de alcance"}]
    response = post_strike(client, [simple_definition(1), simple_definition(2)], exclusions=exclusions)
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "COMPLETE"
    assert "UC-002" not in body["scope"]["selected_coverage_unit_ids"]


def test_invalid_exclusion_returns_400(client):
    exclusions = [{"id": "EX-1", "coverage_unit_id": "UC-999", "reason": "Fuera de alcance"}]
    response = post_strike(client, [simple_definition()], exclusions=exclusions)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_EXCLUSIONS"


def test_complete_dto_has_required_sections(client):
    body = post_strike(client, [simple_definition()]).get_json()
    assert set(("sources", "scope", "coverage", "coverage_summary", "plan", "definition_gaps", "execution", "traceability", "diagnostics")) <= set(body)
    assert body["plan"]["tests"]
    unit = body["coverage"]["units"][0]
    assert set(("id", "statement", "importance", "existing_coverage", "selected", "designability", "source_refs", "definition_gap_id")) <= set(unit)


def test_unexpected_backend_exception_is_sanitized(client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("SECRET INTERNAL DETAIL")
    monkeypatch.setattr(breakers_app, "execute_strike_request", boom)
    response = client.post("/api/strike", data={}, content_type="multipart/form-data")
    assert response.status_code == 500
    body = response.get_json()
    assert body["error"]["code"] == "STRIKE_INTERNAL_ERROR"
    assert "SECRET" not in response.get_data(as_text=True)


def test_per_file_limit_is_transport_configuration(client):
    breakers_app.app.config["STRIKE_MAX_FILE_BYTES"] = 8
    response = post_strike(client, [("large.txt", "El usuario puede cancelar.")])
    assert response.status_code == 413
    assert response.get_json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
