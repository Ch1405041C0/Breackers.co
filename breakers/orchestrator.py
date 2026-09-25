from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from .analyzers import analyzers_for, analyze_requirements_file
from .inputs import detect_input
from .inputs.repository import clone_repository, is_remote_repository
from .report import build_report
from .risk.engine import assess_risks
from .scanners import GitleaksScanner, TrivyScanner

PASSIVE_SCANNERS = (TrivyScanner, GitleaksScanner)
OPTIONAL_ENGINES = (("SonarQube", "sonar-scanner"), ("OWASP ZAP", "zap.sh"), ("JMeter", "jmeter"))


def _scan_local_target(target: str, public_target: str | None = None, source_overrides: dict | None = None) -> dict:
    source = detect_input(target)
    if source_overrides:
        source.update(source_overrides)
    analyzers = analyzers_for(source["type"])
    engines, findings, candidate_risks, limitations = [], [], [], []

    if source["type"] == "functional_document":
        candidate_risks, limitations = analyze_requirements_file(target)

    # Repository scanners inspect files only; SCAN never executes repository code.
    if source["type"] == "repository":
        for scanner_type in PASSIVE_SCANNERS:
            scanner = scanner_type()
            if scanner.available() and scanner.supports(target):
                engines.append(scanner.name)
                findings.extend(scanner.scan(target))
        for name, executable in OPTIONAL_ENGINES:
            if shutil.which(executable):
                engines.append(name)

    risks = assess_risks(candidate_risks)
    report = build_report(public_target or target, engines, findings)
    report["source"] = source
    report["analyzers"] = analyzers
    report["risks"] = [risk.to_dict() for risk in risks]
    report["risk_summary"] = {"identified": len(risks), "limitations": limitations}
    report["risk_contract"] = "v0.1"
    return report


def run_scan(target: str) -> dict:
    target = str(target or "").strip()
    if is_remote_repository(target):
        with TemporaryDirectory(prefix="breakers-repo-") as tmp:
            workspace = Path(tmp) / "repository"
            clone_repository(target, workspace)
            return _scan_local_target(
                str(workspace),
                public_target=target,
                source_overrides={
                    "type": "repository",
                    "target": target,
                    "workspace": "temporary_clone",
                },
            )

    if not Path(target).exists():
        raise ValueError("SCAN v0.1 accepts authorized local evidence or a public GitHub/GitLab repository URL.")

    return _scan_local_target(target)
