from collections import Counter
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from .analyzers import analyzers_for, analyze_requirements_document
from .engine.integration import analyze_scan_report
from .inputs import detect_input
from .inputs.repository import clone_repository, is_remote_repository, repository_commit_sha
from .observability import log_scan_event
from .providers import build_vision_provider
from .report import build_report
from .risk.engine import assess_risks
from .scanners import GitleaksScanner, TrivyScanner

PASSIVE_SCANNERS = (TrivyScanner, GitleaksScanner)
OPTIONAL_ENGINES = (("SonarQube", "sonar-scanner"), ("OWASP ZAP", "zap.sh"), ("JMeter", "jmeter"))


def _emit(progress, stage: str) -> None:
    if progress:
        progress(stage)


def _repository_file_summary(target: str) -> tuple[int, dict[str, int]]:
    extensions: Counter[str] = Counter()
    total = 0
    for _current, directories, filenames in os.walk(target):
        directories[:] = [name for name in directories if name != ".git"]
        for filename in filenames:
            total += 1
            extensions[Path(filename).suffix.lower() or "[sin_extension]"] += 1
    return total, dict(sorted(extensions.items()))


def _safe_scanner_error(error: str) -> str:
    if error.startswith("timeout after ") and error.endswith("s"):
        return error
    prefix = "scanner exited with code "
    if error.startswith(prefix) and error[len(prefix):].isdigit():
        return error
    known_errors = {
        "target is not supported",
        "scanner executable could not be started",
        "scanner completed without producing its JSON report",
        "scanner produced an unreadable JSON report",
    }
    return error if error in known_errors else "El analizador no pudo completar la ejecución."


def _scan_local_target(
    target: str,
    public_target: str | None = None,
    source_overrides: dict | None = None,
    progress=None,
    job_id: str | None = None,
) -> dict:
    _emit(progress, "identifying")
    source = detect_input(target)
    if source_overrides:
        source.update(source_overrides)
    if source["type"] == "repository" and "commit_sha" not in source:
        commit_sha = repository_commit_sha(target)
        if commit_sha:
            source["commit_sha"] = commit_sha
    _emit(progress, "planning")
    analyzers = analyzers_for(source["type"])
    engines, findings, candidate_risks, limitations = [], [], [], []
    required_engines, unavailable_engines, failed_engines = [], [], []
    document_analysis = None

    if source["type"] != "repository":
        log_scan_event(
            "analyzers_selected",
            job_id,
            category="technical",
            required_engines=[],
            analyzers=analyzers,
        )

    if source["type"] == "repository":
        files_total, extensions = _repository_file_summary(target)
        log_scan_event("files_discovered", job_id, total=files_total, by_extension=extensions)

    _emit(progress, "scanning")
    if source["type"] == "functional_document":
        analyzer_started = perf_counter()
        log_scan_event("analyzer_started", job_id, name="requirements", status="started")
        try:
            vision_provider = build_vision_provider()
            candidate_risks, limitations, document_analysis = analyze_requirements_document(
                target,
                vision_provider=vision_provider,
            )
        except Exception:
            log_scan_event(
                "analyzer_failed",
                job_id,
                name="requirements",
                status="error",
                duration_ms=round((perf_counter() - analyzer_started) * 1000),
                error="El analizador de requisitos produjo un error inesperado.",
            )
            raise
        log_scan_event(
            "analyzer_completed",
            job_id,
            name="requirements",
            status="executed",
            duration_ms=round((perf_counter() - analyzer_started) * 1000),
            findings=len(candidate_risks),
        )

    if source["type"] == "repository":
        required_engines = [scanner_type.name for scanner_type in PASSIVE_SCANNERS]
        log_scan_event(
            "analyzers_selected",
            job_id,
            category="technical",
            required_engines=required_engines,
            analyzers=analyzers,
        )
        for scanner_type in PASSIVE_SCANNERS:
            scanner = scanner_type()
            started = perf_counter()
            if not scanner.available():
                unavailable_engines.append(scanner.name)
                log_scan_event(
                    "analyzer_unavailable",
                    job_id,
                    name=scanner.name,
                    status="unavailable",
                    duration_ms=0,
                    error="El ejecutable del analizador no está disponible.",
                )
                continue
            if not scanner.supports(target):
                error = "target is not supported"
                failed_engines.append({"engine": scanner.name, "error": error})
                log_scan_event(
                    "analyzer_failed",
                    job_id,
                    name=scanner.name,
                    status="error",
                    duration_ms=round((perf_counter() - started) * 1000),
                    error=error,
                )
                continue

            log_scan_event("analyzer_started", job_id, name=scanner.name, status="started")
            try:
                result = scanner.scan(target)
            except Exception:
                log_scan_event(
                    "analyzer_failed",
                    job_id,
                    name=scanner.name,
                    status="error",
                    duration_ms=round((perf_counter() - started) * 1000),
                    error="El analizador produjo un error inesperado.",
                )
                raise
            duration_ms = round((perf_counter() - started) * 1000)
            if result.status == "completed":
                engines.append(scanner.name)
                findings.extend(result.findings)
                log_scan_event(
                    "analyzer_completed",
                    job_id,
                    name=scanner.name,
                    status="executed",
                    duration_ms=duration_ms,
                    findings=len(result.findings),
                )
            else:
                error = _safe_scanner_error(result.error or "scanner failed")
                failed_engines.append({"engine": scanner.name, "error": error})
                log_scan_event(
                    "analyzer_failed",
                    job_id,
                    name=scanner.name,
                    status="error",
                    duration_ms=duration_ms,
                    error=error,
                )

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
        coverage_complete_override=(document_analysis["status"] == "COMPLETE") if document_analysis else None,
    )
    report["source"] = source
    report["analyzers"] = analyzers
    report["risks"] = [risk.to_dict() for risk in risks]
    report["risk_summary"] = {"identified": len(risks), "limitations": limitations}
    report["risk_contract"] = "v0.1"
    if document_analysis is not None:
        report["document_analysis"] = document_analysis

    report["agentic_analysis"] = analyze_scan_report(report, job_id=job_id)
    report["agentic_contract"] = "v0.1"
    severity_counts = Counter(item["severity"] for item in report["findings"])
    category_counts = Counter(item["category"] for item in report["findings"])
    log_scan_event(
        "findings_generated",
        job_id,
        total=len(report["findings"]),
        severities=dict(sorted(severity_counts.items())),
        categories=dict(sorted(category_counts.items())),
    )
    log_scan_event(
        "scan_completed",
        job_id,
        analysis_status=report["analysis_status"],
        coverage=report["summary"]["coverage_complete"],
        unavailable_engines=report["unavailable_engines"],
        failed_engines=report["failed_engines"],
        score=report["score"],
    )
    return report


def run_scan(target: str, progress=None, job_id: str | None = None) -> dict:
    target = str(target or "").strip()
    _emit(progress, "received")
    if is_remote_repository(target):
        _emit(progress, "identifying")
        started = perf_counter()
        with TemporaryDirectory(prefix="breakers-repo-") as tmp:
            workspace = Path(tmp) / "repository"
            try:
                clone_repository(target, workspace)
            except Exception:
                log_scan_event(
                    "repository_fetched",
                    job_id,
                    success=False,
                    commit_sha=None,
                    duration_ms=round((perf_counter() - started) * 1000),
                    error="No se pudo obtener el repositorio remoto.",
                )
                raise
            commit_sha = repository_commit_sha(workspace)
            log_scan_event(
                "repository_fetched",
                job_id,
                success=True,
                commit_sha=commit_sha,
                duration_ms=round((perf_counter() - started) * 1000),
            )
            return _scan_local_target(
                str(workspace),
                public_target=target,
                source_overrides={
                    "type": "repository",
                    "target": target,
                    "workspace": "temporary_clone",
                    **({"commit_sha": commit_sha} if commit_sha else {}),
                },
                progress=progress,
                job_id=job_id,
            )

    if not Path(target).exists():
        raise ValueError("SCAN v0.1 accepts authorized local evidence or a public GitHub/GitLab repository URL.")

    return _scan_local_target(target, progress=progress, job_id=job_id)
