ANALYZER_REGISTRY = {"functional_document": ["requirements"], "screen": ["ui_flow"], "api_artifact": ["api_contract"], "repository": ["repository"], "test_evidence": ["coverage"]}

def analyzers_for(input_type: str) -> list[str]:
    return ANALYZER_REGISTRY.get(input_type, [])
