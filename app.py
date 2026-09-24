from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
import subprocess, json, shutil, os, urllib.request, urllib.parse, uuid, datetime, tempfile, re, zipfile, hashlib

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


DOC_EXTENSIONS={".pdf",".docx",".txt",".md"}
UPLOAD_EXTENSIONS=DOC_EXTENSIONS|{".zip",".apk",".aab"}

def extract_document_text(path):
    ext=path.suffix.lower()
    try:
        if ext in (".txt",".md"):
            return path.read_text(encoding="utf-8",errors="ignore")
        if ext==".pdf":
            from pypdf import PdfReader
            return "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
        if ext==".docx":
            from docx import Document
            doc=Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return ""
    return ""

def document_finding(severity,title,evidence,category="Documentación"):
    x=finding("BREAKERS Document Review",severity,title,evidence)
    x["category"]=category
    return x

def analyze_document(path, findings):
    text=extract_document_text(path)
    compact=re.sub(r"\s+"," ",text).strip()
    low=compact.lower()
    if len(compact)<120:
        findings.append(document_finding("HIGH","Documento con información insuficiente","No hay contenido suficiente para evaluar alcance, reglas y escenarios.","Completitud"))
        return
    checks=[
      ("criterio de aceptación|criterios de aceptación|acceptance criteria","MEDIUM","No se identifican criterios de aceptación","Definir resultados observables que permitan determinar cuándo el comportamiento es correcto.","Testabilidad"),
      ("error|excepción|excepcion|timeout|rechazo|fallo","HIGH","Manejo de errores y excepciones no explicitado","No se identificó una definición clara de errores, excepciones, rechazos o timeouts.","Flujos alternativos"),
      ("rol|roles|permiso|permisos|autoriz","HIGH","Roles y permisos no explicitados","No se identificó una definición clara de actores, roles o permisos.","Seguridad"),
      ("api|endpoint|servicio|integración|integracion","MEDIUM","Integraciones técnicas no explicitadas","No se identificaron contratos, endpoints o dependencias de integración.","Dependencias"),
      ("límite|limite|máximo|maximo|mínimo|minimo|rango","MEDIUM","Límites y validaciones no explicitados","No se identificaron límites, rangos o restricciones de los datos de entrada.","Validaciones"),
      ("auditor|log|traza|trazabilidad|monitore","LOW","Trazabilidad u observabilidad no explicitada","No se identificó cómo registrar, auditar u observar el comportamiento del flujo.","Observabilidad"),
    ]
    for pattern,sev,title,evidence,cat in checks:
        if not re.search(pattern,low):
            findings.append(document_finding(sev,title,evidence,cat))
    vague=re.findall(r"\b(?:etc(?:étera)?|según corresponda|cuando aplique|de ser necesario|normalmente|adecuadamente)\b",low)
    if vague:
        findings.append(document_finding("MEDIUM","Lenguaje potencialmente ambiguo",f"Se detectaron {len(vague)} expresiones que pueden admitir más de una interpretación.","Ambigüedad"))
    if "http://" in low:
        findings.append(document_finding("MEDIUM","Referencia técnica sin HTTPS", "El documento contiene al menos una referencia HTTP; revisar si corresponde a un entorno controlado o si debe exigirse TLS.","Seguridad"))
    return text

def fingerprint_finding(x):
    raw="|".join(str(x.get(k,"")).strip().lower() for k in ("engine","category","severity","title","evidence"))
    return hashlib.sha256(raw.encode("utf-8",errors="ignore")).hexdigest()[:16]

def normalize_findings(items):
    severity_rank={"CRITICAL":4,"HIGH":3,"ERROR":3,"MEDIUM":2,"WARNING":2,"LOW":1,"INFO":0,"UNKNOWN":0}
    seen=set(); normalized=[]
    for raw in items:
        x=dict(raw)
        x["severity"]=str(x.get("severity","UNKNOWN")).upper()
        x["fingerprint"]=fingerprint_finding(x)
        if x["fingerprint"] in seen:
            continue
        seen.add(x["fingerprint"])
        normalized.append(x)
    return sorted(normalized,key=lambda x:severity_rank.get(x["severity"],0),reverse=True)

def summarize_result(findings):
    weights={"CRITICAL":10,"HIGH":6,"ERROR":6,"MEDIUM":3,"WARNING":3,"LOW":1,"INFO":1,"UNKNOWN":1}
    ordered=normalize_findings(findings)
    penalty=sum(weights.get(x["severity"],1) for x in ordered)
    risk_keys={(x.get("category",x.get("engine","BREAKERS")),x["severity"]) for x in ordered}
    return ordered, ordered[:3], len(risk_keys), max(0,100-min(100,penalty))

def safe_extract_zip(src, dst):
    with zipfile.ZipFile(src) as z:
        root=Path(dst).resolve()
        for info in z.infolist():
            out=(root/info.filename).resolve()
            if root not in out.parents and out != root:
                raise ValueError("invalid archive path")
            if info.file_size > 50*1024*1024:
                raise ValueError("archive member too large")
        z.extractall(root)

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
    return jsonify(scan_id=sid,status=record["status"],engines=record["engines"],findings=record["preview"],total_findings=record["total_findings"],prioritized_risks=record["prioritized_risks"],score=record["score"],coverage=record.get("coverage",[]),limitations=record.get("limitations",[]),report_locked=not record.get("paid",False))


@app.post("/api/scan/upload")
def scan_upload():
    if str(request.form.get("authorized","")).lower() not in ("1","true","yes"):
        return jsonify(error="authorization required"),400
    asset_type=str(request.form.get("asset_type","file"))
    up=request.files.get("file")
    if not up or not up.filename:
        return jsonify(error="file required"),400
    ext=Path(up.filename).suffix.lower()
    if ext not in UPLOAD_EXTENSIONS:
        return jsonify(error="unsupported file type"),400
    findings=[]; engines=[]
    with tempfile.TemporaryDirectory(prefix="breakers-upload-") as td:
        source=Path(td)/("input"+ext)
        up.save(source)
        if source.stat().st_size > 100*1024*1024:
            return jsonify(error="file too large"),413
        target=source
        if ext in DOC_EXTENSIONS or asset_type=="document":
            engines.append("BREAKERS Document Review")
            analyze_document(source,findings)
        else:
            if ext in (".zip",".apk",".aab"):
                unpack=Path(td)/"unpacked";unpack.mkdir()
                try: safe_extract_zip(source,unpack)
                except Exception: return jsonify(error="invalid or unsafe archive"),400
                target=unpack
            if shutil.which("trivy"): engines.append("Trivy"); add_trivy(target,findings)
            if shutil.which("gitleaks"): engines.append("Gitleaks"); add_gitleaks(target,findings)
            if shutil.which("semgrep"): engines.append("Semgrep"); add_semgrep(target,findings)
    ordered,preview,prioritized_risks,score=summarize_result(findings)
    sid=scan_id()
    coverage=(["completitud","ambigüedad","validaciones","seguridad documental","dependencias","testabilidad"] if asset_type=="document" or ext in DOC_EXTENSIONS else ["código","dependencias","configuración","secretos"])
    limitations=(["No verifica comportamiento real, APIs, performance ni seguridad dinámica en esta etapa."] if asset_type=="document" or ext in DOC_EXTENSIONS else ["El análisis cubre únicamente los motores disponibles en este entorno."])
    record={"scan_id":sid,"created_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"status":"READY","asset_type":asset_type,"target":up.filename,"engines":engines,"findings":ordered,"preview":preview,"total_findings":len(ordered),"prioritized_risks":prioritized_risks,"score":score,"coverage":coverage,"limitations":limitations,"paid":False}
    save_scan(record)
    return jsonify(scan_id=sid,status="READY",engines=engines,findings=preview,total_findings=len(ordered),prioritized_risks=prioritized_risks,score=score,coverage=coverage,limitations=limitations,report_locked=bool(ordered),mode="authorized-upload")

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
    # Persist the complete result server-side. Only the preview is returned before verified payment.
    ordered,preview,prioritized_risks,score=summarize_result(findings)
    sid=scan_id()
    asset_type=str(d.get("asset_type","unknown"))
    remote_only=not bool(p)
    status="LIMITED" if remote_only else "READY"
    coverage=(["capacidad de análisis detectada"] if remote_only else ["código","dependencias","configuración","secretos"])
    limitations=(["Objetivo remoto preparado, pero no se ejecutan DAST, carga ni navegación activa automáticamente. Requiere una ejecución configurada y autorizada."] if remote_only else ["La cobertura depende de los motores disponibles en el entorno BREAKERS."])
    record={"scan_id":sid,"created_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"status":status,"asset_type":asset_type,"target":target,"engines":engines,"findings":ordered,"preview":preview,"total_findings":len(ordered),"prioritized_risks":prioritized_risks,"score":score,"coverage":coverage,"limitations":limitations,"paid":False}
    save_scan(record)
    if tempdir: tempdir.cleanup()
    return jsonify(scan_id=sid,status=status,engines=engines,tools=installed_tools(),findings=preview,total_findings=len(ordered),prioritized_risks=prioritized_risks,score=score,coverage=coverage,limitations=limitations,report_locked=bool(ordered),mode="authorized-safe")

if __name__=="__main__":
    app.run(host="0.0.0.0",port=8080,debug=False)
