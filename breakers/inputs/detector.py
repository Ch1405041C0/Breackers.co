from pathlib import Path
from urllib.parse import urlparse

SCAN_INPUT_TYPES = {"web", "repository", "api", "app", "file"}

DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".md"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
API_EXTENSIONS = {".yaml", ".yml", ".json"}
TEST_EXTENSIONS = {".csv", ".xlsx"}
APP_EXTENSIONS = {".apk", ".ipa"}
LOG_EXTENSIONS = {".log"}
MARKUP_EXTENSIONS = {".xml", ".html"}
ARCHIVE_EXTENSIONS = {".zip"}


def _is_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _file_subtype(suffix: str) -> str:
    if suffix in DOCUMENT_EXTENSIONS:
        return "document"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in API_EXTENSIONS:
        return "structured_data"
    if suffix in TEST_EXTENSIONS:
        return "test_evidence"
    if suffix in LOG_EXTENSIONS:
        return "log"
    if suffix in MARKUP_EXTENSIONS:
        return "markup"
    if suffix in ARCHIVE_EXTENSIONS:
        return "archive"
    return "generic_file"


def identify_input(target: str, declared_type: str) -> dict:
    """Identify one of the five SCAN product input families without analyzing it."""
    value = str(target or "").strip()
    input_type = str(declared_type or "").strip().lower()
    if input_type not in SCAN_INPUT_TYPES:
        raise ValueError(f"unsupported SCAN input_type: {input_type or 'missing'}")
    if not value:
        raise ValueError("SCAN input target is required")

    suffix = Path(value).suffix.lower()
    result = {
        "input_type": input_type,
        "target": value,
        "identified": True,
    }

    if input_type == "web":
        result.update({
            "subtype": "website",
            "locator": "url" if _is_http_url(value) else "reference",
        })
        return result

    if input_type == "repository":
        result.update({
            "subtype": "repository",
            "locator": "url" if _is_http_url(value) else "path_or_reference",
        })
        return result

    if input_type == "api":
        result.update({
            "subtype": "api_contract" if suffix in API_EXTENSIONS else "api_reference",
            "locator": "url" if _is_http_url(value) else "path_or_reference",
            "extension": suffix or None,
        })
        return result

    if input_type == "app":
        app_subtype = {
            ".apk": "android_apk",
            ".ipa": "ios_ipa",
        }.get(suffix, "mobile_app")
        result.update({
            "subtype": app_subtype,
            "locator": "upload_or_path",
            "extension": suffix or None,
        })
        return result

    result.update({
        "subtype": _file_subtype(suffix),
        "locator": "upload_or_path",
        "extension": suffix or None,
    })
    return result


def detect_input(target: str) -> dict:
    """Legacy analyzer routing used by the current SCAN execution pipeline."""
    path = Path(target)
    if path.is_dir():
        return {"type": "repository", "target": target}
    suffix = path.suffix.lower()
    if suffix in DOCUMENT_EXTENSIONS:
        kind = "functional_document"
    elif suffix in IMAGE_EXTENSIONS:
        kind = "screen"
    elif suffix in API_EXTENSIONS:
        kind = "api_artifact"
    elif suffix in TEST_EXTENSIONS:
        kind = "test_evidence"
    else:
        kind = "unknown"
    return {"type": kind, "target": target}
