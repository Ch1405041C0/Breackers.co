# BREAKERS — Engine Catalog

BREAKERS uses external tools as specialized sensors. Their output is normalized and correlated by the BREAKERS Risk Engine. A tool appearing here does not mean it is already integrated.

| Engine | Input / stage | Purpose | Status |
| --- | --- | --- | --- |
| BREAKERS Requirements Analyzer | functional text | ambiguity, conditions, boundaries, missing exception behavior | integrated v0.1 |
| Trivy | repository / build artifacts | vulnerabilities, misconfiguration, secrets | integrated |
| Gitleaks | repository | secrets | integrated |
| SonarQube / SonarScanner | source code | static quality analysis | detected, execution configuration pending |
| OWASP ZAP | running web/API | DAST | detected, authorized execution configuration pending |
| JMeter | running service/API | performance | detected, test-plan configuration pending |
| Spectral | OpenAPI / structured specs | contract linting and custom rules | next integration |
| Schemathesis | OpenAPI / GraphQL | property-based API testing and edge cases | next integration |
| Semgrep | source code | static rules and risky patterns | catalogued |
| axe-core | rendered web UI | accessibility | catalogued |
| Pa11y | web UI | automated accessibility checks | catalogued |
| k6 | running service/API | load/performance | catalogued |
| OWASP Dependency-Check | dependencies | known vulnerable dependencies | catalogued |
| BackstopJS | rendered UI | visual regression | catalogued |

## Carousel rule
Whenever an external engine is actually adopted by BREAKERS, its name and visual identity must be added to the SCAN engine carousel with an explicit status (integrated, detected/configurable, next, or catalogued). Do not present a catalogued tool as integrated.

## Product rule
Tools are implementation details. BREAKERS chooses them according to the evidence and project stage; the user should not need to know which scanner to run. Findings become evidence for BREAKERS risks rather than isolated vendor reports.
