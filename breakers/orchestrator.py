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


def _emit(progress, stage: str) -> None:
    if progress:
        progress(stage)


def _scan_local_target(target: str, public_target: str | None = None, source_overrides: dict | None = None, progress=None) -> dict:
    _emit(progress, "identifying")
    source = detect_input(target)
    if source_overrides:
        source.update(source_overrides)
    _emit(progress, "planning")
    analyzers = analyzers_for(source["type"])
    engines, findings, candidate_risks, limitations = [], [], [], []
    required_engines, unavailable_engines, failed_engines = [], [], []

    _emit(progress, "scanning")
    if source["type"] == "functional_document":
        candidate_risks, limitations = analyze_requirements_file(target)

    # Repository scanners inspect files only; SCAN never executes repository code.
    if source["type"] == "repository":
        required_engines = [scanner_type.name for scanner_type in PASSIVE_SCANNERS]
        for scanner_type in PASSIVE_SCANNERS:
            scanner = scanner_type()
            if not scanner.available():
                unavailable_engines.append(scanner.name)
                continue
            if not scanner.supports(target):
                failed_engines.append({"engine": scanner.name, "error": "target is not supported"})
                continue

            result = scanner.scan(target)
            if result.status == "completed":
                engines.append(scanner.name)
                findings.extend(result.findings)
            else:
                failed_engines.append({"engine": scanner.name, "error": result.error or "scanner failed"})

    _emit(progress, "checking")
    _emit(progress, "evidence")
    _emit(progress, "prioritizing")
    risks = assess_risks(candidate_risks)
    _emit(progress, "reporting")
    report = build_report(
        public_target or target,
        engines,
        findings,
        required_engines=required_engines,
        unavailable_engines=unavailable_engines,
        failed_engines=failed_engines,
    )
    report["source"] = source
    report["analyzers"] = analyzers
    report["risks"] = [risk.to_dict() for risk in risks]
    report["risk_summary"] = {"identified": len(risks), "limitations": limitations}
    report["risk_contract"] = "v0.1"
    return report


def run_scan(target: str, progress=None) -> dict:
    target = str(target or "").strip()
    _emit(progress, "received")
    if is_remote_repository(target):
        _emit(progress, "identifying")
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
                progress=progress,
            )

    if not Path(target).exists():
        raise ValueError("SCAN v0.1 accepts authorized local evidence or a public GitHub/GitLab repository URL.")

    return _scan_local_target(target, progress=progress)
