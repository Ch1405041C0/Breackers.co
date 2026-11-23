from pathlib import Path

path = Path("index.html")
content = path.read_text(encoding="utf-8")

marker = '<section class="content" id="productos"'

html = r'''
<section class="breakers-security" aria-labelledby="breakers-security-title">
  <div class="wrap">

    <div class="breakers-security-heading">
      <span class="small-label">BREAKERS / SEGURIDAD</span>

      <h2 id="breakers-security-title">
        TUS DATOS. TUS REGLAS.
      </h2>

      <p>
        Breakers está diseñado para adaptarse a la infraestructura
        y las políticas de seguridad de cada organización.
      </p>
    </div>

    <div class="breakers-security-grid">

      <div class="breakers-security-item">
        <span class="breakers-security-number">01</span>
        <h3>CLOUD</h3>
        <p>AWS · Azure · GCP</p>
      </div>

      <div class="breakers-security-item">
        <span class="breakers-security-number">02</span>
        <h3>VPC PRIVADA</h3>
        <p>Infraestructura controlada por tu organización.</p>
      </div>

      <div class="breakers-security-item">
        <span class="breakers-security-number">03</span>
        <h3>ON-PREMISE</h3>
        <p>Despliegue dentro de tus propios servidores.</p>
      </div>

      <div class="breakers-security-item">
        <span class="breakers-security-number">04</span>
        <h3>MODEL AGNOSTIC</h3>
        <p>OpenAI · Claude · Llama · Ollama / local · otros modelos.</p>
      </div>

    </div>

    <p class="breakers-security-note">
      La arquitectura puede adaptarse al entorno, las restricciones
      y el modelo de IA definido por cada organización.
    </p>

  </div>
</section>

'''

if content.count(marker) != 1:
    raise RuntimeError(
        f"Esperaba encontrar la sección productos una vez; encontré "
        f"{content.count(marker)}. No se modificó index.html."
    )

if 'class="breakers-security"' in content:
    raise RuntimeError(
        "La sección BREAKERS SECURITY ya existe. No se modificó index.html."
    )

content = content.replace(marker, html + marker, 1)

with path.open("w", encoding="utf-8", newline="") as f:
    f.write(content)

print("OK - HTML BREAKERS SECURITY agregado")