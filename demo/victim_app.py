"""Tiny demo target for the BREAKERS deployment gate.

Set DEMO_BROKEN=true to simulate a hotfix regression: the Save button
stops updating the dashboard message.
"""
from flask import Flask, render_template_string
import os

app = Flask(__name__)
BROKEN = os.environ.get("DEMO_BROKEN", "false").lower() == "true"

PAGE = """<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><title>BREAKERS Gate Demo</title>
<style>body{font-family:Arial;background:#070907;color:#f3f4ed;max-width:720px;margin:80px auto}button{background:#d0f77a;border:0;padding:14px 24px;font-weight:700}.card{border:1px solid #384038;padding:28px;border-radius:12px}input{padding:12px;width:65%;margin-right:10px}</style></head>
<body><div class="card"><h1>Demo App</h1><p>Hotfix candidato a producción</p>
<input id="name" value="BREAKERS"><button id="save">Guardar</button>
<p id="status">Sin cambios</p></div>
<script>
document.querySelector('#save').addEventListener('click', () => {
  if (!{{ broken|tojson }}) document.querySelector('#status').textContent = 'Guardado correctamente';
});
</script></body></html>"""

@app.get("/")
def index():
    return render_template_string(PAGE, broken=BROKEN)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8090, debug=False)
