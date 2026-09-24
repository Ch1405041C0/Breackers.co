from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
import subprocess, json, shutil, tempfile, csv
app=Flask(__name__)
ROOT=Path(__file__).parent

def run(cmd, timeout=120):
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
        return p.returncode,p.stdout,p.stderr
    except Exception as e:return 127,'',str(e)

def finding(engine,severity,title,evidence):return {'engine':engine,'severity':severity,'title':title,'evidence':evidence}

@app.get('/')
def index(): return send_from_directory(ROOT,'index.html')

@app.post('/api/scan')
def scan():
    d=request.get_json(force=True) or {}; target=str(d.get('target','')).strip()
    if not d.get('authorized') or not target:return jsonify(error='authorization and target required'),400
    # Safe MVP: inventory + passive/local artifact adapters. Active DAST/load must be configured explicitly server-side.
    engines=[]; findings=[]
    if shutil.which('trivy') and Path(target).exists():
        engines.append('Trivy'); out=ROOT/'trivy.json'; run(['trivy','fs','--scanners','vuln,misconfig,secret','--format','json','-o',str(out),target],180)
        if out.exists():
            try:
                j=json.loads(out.read_text());
                for r in j.get('Results',[]):
                    for v in r.get('Vulnerabilities') or []: findings.append(finding('Trivy',v.get('Severity','UNKNOWN'),v.get('VulnerabilityID','Vulnerability'),v.get('Title') or v.get('PkgName','')))
                    for m in r.get('Misconfigurations') or []: findings.append(finding('Trivy',m.get('Severity','UNKNOWN'),m.get('Title','Misconfiguration'),m.get('Message','')))
                    for z in r.get('Secrets') or []: findings.append(finding('Trivy','HIGH',z.get('Title','Secret detected'),z.get('RuleID','')))
            except Exception: pass
    if shutil.which('gitleaks') and Path(target).exists():
        engines.append('Gitleaks'); out=ROOT/'gitleaks.json'; run(['gitleaks','dir',target,'--report-format','json','--report-path',str(out),'--no-banner'],120)
        if out.exists():
            try:
                for x in json.loads(out.read_text() or '[]'): findings.append(finding('Gitleaks','HIGH',x.get('Description','Secret detected'),f"{x.get('File','')}:{x.get('StartLine','')}"))
            except Exception: pass
    # SonarQube/ZAP/JMeter adapters are intentionally configuration-driven: credentials, plans and authorized scope belong on server.
    for name,exe in [('SonarQube','sonar-scanner'),('OWASP ZAP','zap.sh'),('JMeter','jmeter')]:
        if shutil.which(exe): engines.append(name)
    weights={'CRITICAL':10,'HIGH':6,'MEDIUM':3,'LOW':1,'UNKNOWN':1}
    penalty=sum(weights.get(str(x['severity']).upper(),1) for x in findings)
    return jsonify(engines=engines,findings=findings[:200],score=max(0,100-min(100,penalty)),mode='safe')

if __name__=='__main__': app.run(host='127.0.0.1',port=8080,debug=True)
