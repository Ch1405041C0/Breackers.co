import io

import app as breakers_app

from breakers.inputs import identify_input
from breakers.planning import plan_scan_engines


def engine_ids(plan):
    return [item["id"] for item in plan["engines"]]


def test_web_plan_selects_web_engines_without_execution():
    source = identify_input("https://staging.example.com", "web")
    plan = plan_scan_engines(source)
    assert engine_ids(plan) == ["zap", "axe", "pa11y", "backstop"]
    assert plan["execution_started"] is False
    assert all(item["will_execute"] is False for item in plan["engines"])


def test_repository_plan_selects_integrated_and_catalogued_code_engines():
    source = identify_input("https://github.com/acme/project", "repository")
    plan = plan_scan_engines(source)
    assert plan["analyzers"] == ["repository"]
    assert engine_ids(plan) == ["trivy", "gitleaks", "sonar", "semgrep", "dependency_check"]
    status = {item["id"]: item["status"] for item in plan["engines"]}
    assert status["trivy"] == "integrated"
    assert status["gitleaks"] == "integrated"
    assert status["sonar"] == "detected_config_pending"


def test_api_contract_plan_selects_contract_engines():
    source = identify_input("openapi.json", "api")
    plan = plan_scan_engines(source)
    assert plan["analyzers"] == ["api_contract"]
    assert engine_ids(plan) == ["spectral", "schemathesis"]


def test_api_runtime_reference_selects_runtime_engines():
    source = identify_input("https://api.example.com", "api")
    plan = plan_scan_engines(source)
    assert source["subtype"] == "api_reference"
    assert engine_ids(plan) == ["zap", "jmeter", "k6"]


def test_app_plan_reports_mobile_engine_gap_instead_of_inventing_one():
    source = identify_input("release.apk", "app")
    plan = plan_scan_engines(source)
    assert plan["engines"] == []
    assert plan["gaps"] == ["mobile application engine is not defined in the BREAKERS engine catalog yet"]


def test_document_file_uses_requirements_analyzer():
    source = identify_input("requirements.docx", "file")
    plan = plan_scan_engines(source)
    assert plan["analyzers"] == ["requirements"]
    assert engine_ids(plan) == ["requirements"]


def test_image_file_registers_ui_flow_but_does_not_invent_external_engine():
    source = identify_input("screen.png", "file")
    plan = plan_scan_engines(source)
    assert plan["analyzers"] == ["ui_flow"]
    assert plan["engines"] == []
    assert plan["gaps"]


def test_plan_endpoint_returns_identification_and_plan():
    client = breakers_app.app.test_client()
    response = client.post("/api/scan/plan", json={
        "input_type": "repository",
        "target": "https://github.com/acme/project",
    })
    assert response.status_code == 200
    body = response.get_json()
    assert body["source"]["input_type"] == "repository"
    assert body["plan"]["execution_started"] is False
    assert "trivy" in engine_ids(body["plan"])


def test_plan_endpoint_accepts_uploaded_app_filename_without_executing_it():
    client = breakers_app.app.test_client()
    response = client.post(
        "/api/scan/plan",
        data={
            "input_type": "app",
            "file": (io.BytesIO(b"not-an-apk"), "release.apk"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["source"]["subtype"] == "android_apk"
    assert body["plan"]["execution_started"] is False
    assert body["plan"]["engines"] == []


def test_plan_endpoint_rejects_unknown_input_type():
    client = breakers_app.app.test_client()
    response = client.post("/api/scan/plan", json={"input_type": "mystery", "target": "x"})
    assert response.status_code == 400
