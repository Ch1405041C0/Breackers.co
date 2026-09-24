from pathlib import Path
import shutil

from .report import build_report
from .scanners import GitleaksScanner, TrivyScanner

PASSIVE_SCANNERS = (TrivyScanner, GitleaksScanner)
OPTIONAL_ENGINES = (("SonarQube", "sonar-scanner"), ("OWASP ZAP", "zap.sh"), ("JMeter", "jmeter"))


def run_scan(target: str) -> dict:
    if not Path(target).exists():
        raise ValueError("SCAN v0.1 only accepts authorized local paths.")

    engines = []
    findings = []
    for scanner_type in PASSIVE_SCANNERS:
        scanner = scanner_type()
        if scanner.available() and scanner.supports(target):
            engines.append(scanner.name)
            findings.extend(scanner.scan(target))

    for name, executable in OPTIONAL_ENGINES:
        if shutil.which(executable):
            engines.append(name)

    return build_report(target, engines, findings)
