from io import BytesIO

import pytest

from app import app
from breakers.inputs import identify_input


@pytest.mark.parametrize(
    ("input_type", "target", "subtype"),
    [
        ("web", "https://staging.example.com", "website"),
        ("repository", "https://github.com/acme/project", "repository"),
        ("api", "https://staging.example.com/openapi.json", "api_contract"),
        ("app", "mobile-release.apk", "android_apk"),
        ("file", "requirements.docx", "document"),
    ],
)
def test_identifies_all_product_input_types(input_type, target, subtype):
    source = identify_input(target, input_type)

    assert source["identified"] is True
    assert source["input_type"] == input_type
    assert source["subtype"] == subtype


def test_file_mode_keeps_file_as_top_level_input():
    source = identify_input("contract.json", "file")

    assert source["input_type"] == "file"
    assert source["subtype"] == "structured_data"


def test_api_mode_takes_precedence_over_file_extension():
    source = identify_input("contract.json", "api")

    assert source["input_type"] == "api"
    assert source["subtype"] == "api_contract"


def test_rejects_unknown_input_type():
    with pytest.raises(ValueError, match="unsupported SCAN input_type"):
        identify_input("anything", "other")


def test_identify_endpoint_accepts_text_input():
    client = app.test_client()

    response = client.post(
        "/api/scan/identify",
        json={"input_type": "web", "target": "https://example.com"},
    )

    assert response.status_code == 200
    assert response.get_json()["source"]["input_type"] == "web"
    assert response.get_json()["source"]["subtype"] == "website"


def test_identify_endpoint_accepts_uploaded_app_filename():
    client = app.test_client()

    response = client.post(
        "/api/scan/identify",
        data={
            "input_type": "app",
            "file": (BytesIO(b"not-an-apk"), "release.apk"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["source"]["input_type"] == "app"
    assert response.get_json()["source"]["subtype"] == "android_apk"
