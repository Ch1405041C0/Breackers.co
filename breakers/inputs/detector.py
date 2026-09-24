from pathlib import Path

DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
API_EXTENSIONS = {".yaml", ".yml", ".json"}
TEST_EXTENSIONS = {".csv", ".xlsx"}

def detect_input(target: str) -> dict:
    path = Path(target)
    if path.is_dir(): return {"type": "repository", "target": target}
    suffix = path.suffix.lower()
    if suffix in DOCUMENT_EXTENSIONS: kind = "functional_document"
    elif suffix in IMAGE_EXTENSIONS: kind = "screen"
    elif suffix in API_EXTENSIONS: kind = "api_artifact"
    elif suffix in TEST_EXTENSIONS: kind = "test_evidence"
    else: kind = "unknown"
    return {"type": kind, "target": target}
