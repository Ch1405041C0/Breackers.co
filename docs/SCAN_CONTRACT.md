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

## Product boundary
SCAN identifies and correlates risk. STRIKE converts accepted/prioritized risk into executable test strategy. CONTROL tracks risk, execution and evidence across versions.

## Technical tools
Trivy, Gitleaks, SonarQube, ZAP and JMeter are adapters used when the source and project stage justify them. They do not define SCAN.
