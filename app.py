from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
import subprocess, json, shutil, os, urllib.request, urllib.parse, uuid, datetime, tempfile

app = Flask(__name__)
ROOT = Path(__file__).parent
SCAN_STORE = ROOT / "data" / "scans"
SCAN_STORE.mkdir(parents=True, exist_ok=True)

TOOLS = [
    ("Trivy", "trivy", "dependencias / configuración / secretos"),
    ("Gitleaks", "gitleaks", "secretos"),
    ("Semgrep", "semgrep", "SAST"),
    ("SonarScanner", "sonar-scanner", "calidad / SAST"),
    ("OWASP ZAP", "zap.sh", "DAST web/API"),
    ("JMeter", "jmeter", "performance"),
    ("Newman", "newman", "API"),
    ("Playwright", "playwright", "E2E"),
]

def run(cmd, timeout=120):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return 127, "", str(e)

def finding(engine, severity, title, evidence):
    return {"engine": engine, "severity": severity, "title": title, "evidence": evidence}

def local_target(value):
    p = Path(value).expanduser().resolve()
    return p if p.exists() else None

def github_public_repo(value):
    """Return a normalized public GitHub clone URL or None."""
    try:
        u=urllib.parse.urlparse(value)
        if u.scheme != "https" or u.netloc.lower() != "github.com":
            return None
        parts=[x for x in u.path.strip("/").split("/") if x]
        if len(parts) != 2:
            return None
        owner, name=parts
        if name.endswith(".git"): name=name[:-4]
        allowed="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        if not owner or not name or any(c not in allowed for c in owner+name):
            return None
        return f"https://github.com/{owner}/{name}.git"
    except Exception:
        return None

def installed_tools():
    return [{"name": name, "available": bool(shutil.which(exe)), "coverage": coverage}
            for name, exe, coverage in TOOLS]

def add_trivy(target, findings):
    out = ROOT / "trivy.json"
    run(["trivy", "fs", "--scanners", "vuln,misconfig,secret", "--format", "json", "-o", str(out), str(target)], 240)
    if not out.exists(): return
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
        for result in data.get("Results", []):
            for v in result.get("Vulnerabilities") or []:
                findings.append(finding("Trivy", v.get("Severity","UNKNOWN"), v.get("VulnerabilityID","Vulnerability"), v.get("Title") or v.get("PkgName","")))
            for m in result.get("Misconfigurations") or []:
                findings.append(finding("Trivy", m.get("Severity","UNKNOWN"), m.get("Title","Misconfiguration"), m.get("Message","")))
            for s in result.get("Secrets") or []:
                findings.append(finding("Trivy", "HIGH", s.get("Title","Secret detected"), s.get("RuleID","")))
    except Exception: pass

def add_gitleaks(target, findings):
    out = ROOT / "gitleaks.json"
    run(["gitleaks","dir",str(target),"--report-format","json","--report-path",str(out),"--no-banner"],180)
    if not out.exists(): return
    try:
        for x in json.loads(out.read_text(encoding="utf-8") or "[]"):
            findings.append(finding("Gitleaks","HIGH",x.get("Description","Secret detected"),f"{x.get('File','')}:{x.get('StartLine','')}"))
    except Exception: pass

def add_semgrep(target, findings):
    code, stdout, _ = run(["semgrep","scan","--config","auto","--json","--quiet",str(target)],240)
    try:
        data=json.loads(stdout or "{}")
        for x in data.get("results",[]):
            extra=x.get("extra",{}); sev=extra.get("severity","INFO")
            findings.append(finding("Semgrep",sev,extra.get("message") or x.get("check_id","Finding"),f"{x.get('path','')}:{x.get('start',{}).get('line','')}"))
    except Exception: pass

def add_sonar(findings):
    host=os.getenv("SONAR_HOST_URL","").rstrip("/")
    token=os.getenv("SONAR_TOKEN","")
    project=os.getenv("SONAR_PROJECT_KEY","")
    if not (host and token and project): return
    try:
        q=urllib.parse.urlencode({"componentKeys":project,"resolved":"false","ps":"100"})
        req=urllib.request.Request(f"{host}/api/issues/search?{q}",headers={"Authorization":"Bearer "+token})
        with urllib.request.urlopen(req,timeout=15) as r: data=json.load(r)
        sevmap={"BLOCKER":"CRITICAL","CRITICAL":"CRITICAL","MAJOR":"HIGH","MINOR":"MEDIUM","INFO":"LOW"}
        for x in data.get("issues",[]):
            findings.append(finding("SonarQube",sevmap.get(x.get("severity"),"UNKNOWN"),x.get("message","Issue"),x.get("component","")))
    except Exception: pass

@app.get("/")
def index(): return send_from_directory(ROOT,"index.html")

@app.get("/checkout.html")
def checkout(): return send_from_directory(ROOT,"checkout.html")

@app.get("/api/tools")
def tools(): return jsonify(tools=installed_tools())

def scan_id():
    return "BRK-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:8].upper()

def save_scan(record):
    path = SCAN_STORE / f"{record['scan_id']}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def load_scan(sid):
    if not sid or not sid.startswith("BRK-") or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-" for c in sid):
        return None
    path = SCAN_STORE / f"{sid}.json"
    if not path.exists(): return None
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return None

@app.get("/api/scan/<sid>/preview")
def scan_preview(sid):
    record=load_scan(sid)
    if not record: return jsonify(error="scan not found"),404
    return jsonify(scan_id=sid,status=record["status"],engines=record["engines"],findings=record["preview"],total_findings=record["total_findings"],prioritized_risks=record["prioritized_risks"],score=record["score"],report_locked=not record.get("paid",False))

@app.post("/api/scan")
def scan():
    d=request.get_json(force=True) or {}
    target=str(d.get("target","")).strip()
    if not d.get("authorized") or not target:
        return jsonify(error="authorization and target required"),400
    p=local_target(target); findings=[]; engines=[]; tempdir=None
    repo_url=github_public_repo(target) if str(d.get("asset_type",""))=="repo" else None
    if not p and repo_url:
        tempdir=tempfile.TemporaryDirectory(prefix="breakers-scan-")
        clone_path=Path(tempdir.name)/"repo"
        code,_,err=run(["git","clone","--depth","1","--",repo_url,str(clone_path)],120)
        if code != 0:
            tempdir.cleanup()
            return jsonify(error="No pudimos leer el repositorio público de GitHub.",detail=err[-300:]),400
        p=clone_path
    if p:
        if shutil.which("trivy"): engines.append("Trivy"); add_trivy(p,findings)
        if shutil.which("gitleaks"): engines.append("Gitleaks"); add_gitleaks(p,findings)
        if shutil.which("semgrep"): engines.append("Semgrep"); add_semgrep(p,findings)
        if shutil.which("sonar-scanner"):
            engines.append("SonarQube")
            add_sonar(findings)
    else:
        # URL targets are inventoried only here. Active DAST/load execution stays explicitly configured.
        for name,exe,_ in TOOLS:
            if name in ("OWASP ZAP","JMeter","Newman","Playwright") and shutil.which(exe): engines.append(name)
    weights={"CRITICAL":10,"HIGH":6,"ERROR":6,"MEDIUM":3,"WARNING":3,"LOW":1,"INFO":1,"UNKNOWN":1}
    penalty=sum(weights.get(str(x["severity"]).upper(),1) for x in findings)
    severity_rank={"CRITICAL":4,"HIGH":3,"ERROR":3,"MEDIUM":2,"WARNING":2,"LOW":1,"INFO":0,"UNKNOWN":0}
    ordered=sorted(findings,key=lambda x:severity_rank.get(str(x.get("severity","UNKNOWN")).upper(),0),reverse=True)
    # Persist the complete result server-side. Only the preview is returned before verified payment.
    preview=ordered[:3]
    risk_keys={(x.get("engine"),str(x.get("severity","UNKNOWN")).upper()) for x in ordered}
    sid=scan_id(); score=max(0,100-min(100,penalty))
    record={"scan_id":sid,"created_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"status":"READY","asset_type":str(d.get("asset_type","unknown")),"target":target,"engines":engines,"findings":ordered,"preview":preview,"total_findings":len(ordered),"prioritized_risks":len(risk_keys),"score":score,"paid":False}
    save_scan(record)
    if tempdir: tempdir.cleanup()
    return jsonify(scan_id=sid,status="READY",engines=engines,tools=installed_tools(),findings=preview,total_findings=len(ordered),prioritized_risks=len(risk_keys),score=score,report_locked=bool(ordered),mode="authorized-safe")

if __name__=="__main__":
    app.run(host="0.0.0.0",port=8080,debug=False)
