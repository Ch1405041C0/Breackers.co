from pathlib import Path
import shutil

from .analyzers import analyzers_for
from .inputs import detect_input
from .report import build_report
from .scanners import GitleaksScanner, TrivyScanner

PASSIVE_SCANNERS = (TrivyScanner, GitleaksScanner)
OPTIONAL_ENGINES = (("SonarQube", "sonar-scanner"), ("OWASP ZAP", "zap.sh"), ("JMeter", "jmeter"))


def run_scan(target: str) -> dict:
    if not Path(target).exists():
        raise ValueError("SCAN v0.1 only accepts authorized local evidence.")

    source = detect_input(target)
    analyzers = analyzers_for(source["type"])
    engines = []
    findings = []

    # Repository tools are one capability of SCAN, not SCAN itself.
    if source["type"] == "repository":
        for scanner_type in PASSIVE_SCANNERS:
            scanner = scanner_type()
            if scanner.available() and scanner.supports(target):
                engines.append(scanner.name)
                findings.extend(scanner.scan(target))
        for name, executable in OPTIONAL_ENGINES:
            if shutil.which(executable): engines.append(name)

    report = build_report(target, engines, findings)
    report["source"] = source
    report["analyzers"] = analyzers
    report["risks"] = []
    report["risk_contract"] = "v0.1"
    return report
