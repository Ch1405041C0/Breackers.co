# BREAKERS SCAN — Contract v0.1

## Purpose
SCAN identifies where a product can fail before the failure becomes a bug. It accepts evidence from any stage of a project and turns observations into traceable risk hypotheses.

## Supported source families
- Functional documents, requirements and stories
- Screens, wireframes and UI evidence
- API artifacts such as OpenAPI/Swagger/Postman exports
- Repositories and local technical artifacts
- Test cases, executions and evidence
- Later adapters: architecture, database schemas, logs and production metrics

## Universal flow
SOURCE -> INPUT DETECTOR -> ANALYZER(S) -> RISK ENGINE -> CORRELATION -> BREAKERS RISKS

SCAN chooses analysis from the evidence available. A tool is an implementation detail, not the product.

## Risk contract
Every risk has stable id, area, severity, title, falsifiable hypothesis, status, confidence, evidence or an explicit missing_evidence declaration, and suggested_action.

## Core rule
BREAKERS must not manufacture findings when evidence is insufficient. It records uncertainty and identifies the missing evidence required to verify or discard a risk.

## Execution status and score
- `completed` means the required analysis coverage ran successfully; an empty findings list is meaningful only for a completed analysis.
- `incomplete` means the objective was received but required coverage was unavailable or unfinished. Do not present this as a clean result; leave the score null and state that there are no conclusive results.
- `failed` means SCAN could not produce a valid report.

## Local Ollama analysis
- SCAN uses `BREAKERS_OLLAMA_MODEL` (default `qwen3:8b`) and `BREAKERS_MODEL_TIMEOUT` (default 120 seconds).
- Both SCAN and STRIKE accept `BREAKERS_OLLAMA_URL`; `BREAKERS_OLLAMA_BASE_URL` remains supported as a fallback for existing deployments.
- SCAN sends one bounded AI analysis per run, uses Ollama JSON-schema output, and disables Qwen thinking with `think: false`. Structured `analyzer_completed`, `analyzer_failed`, and `analyzer_unavailable` logs include the actual model, elapsed time, context/payload byte counts, and generation token counts when available.

## Product boundary
SCAN identifies and correlates risk. STRIKE converts accepted/prioritized risk into executable test strategy. CONTROL tracks risk, execution and evidence across versions.

## Technical tools
Trivy, Gitleaks, SonarQube, ZAP and JMeter are adapters used when the source and project stage justify them. They do not define SCAN.
