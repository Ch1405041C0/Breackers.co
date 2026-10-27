from pathlib import Path
import re

path = Path("index.html")
content = path.read_text(encoding="utf-8")

pattern = re.compile(
    r'<section class="hero"[^>]*>.*?</section>',
    re.DOTALL
)

hero = r'''<section class="hero hero-v2" aria-labelledby="hero-title">
  <div class="wrap">

    <div class="hero-v2-main">

      <div class="hero-v2-copy">
        <span class="small-label">QUALITY ENGINEERING AGÉNTICA</span>

        <h1 id="hero-title">
          Encontrá el<br>
          riesgo.<br>
          <strong>Decidí el<br>
          próximo paso.</strong>
        </h1>

        <p class="hero-v2-lead">
          Analizamos lo que existe hoy en tu proyecto,
          encontramos riesgos y los convertimos en
          decisiones respaldadas por evidencia.
        </p>

        <a class="hero-v2-cta" href="#contacto">
          Solicitar demo
          <span aria-hidden="true">→</span>
        </a>
      </div>

      <div class="hero-v2-demo" aria-label="Demostración de Breakers">
        <div class="hero-v2-demo-frame">
          <button class="hero-v2-demo-button" type="button">
            Ver cómo funciona
            <span aria-hidden="true">▷</span>
          </button>
        </div>
      </div>

    </div>

    <div class="hero-v2-principles">

      <article class="hero-principle">
        <div class="hero-principle-icon" aria-hidden="true">
          <span>▣</span>
        </div>

        <div>
          <h2>PRIVATE<br>BY DESIGN</h2>
          <p>Tus datos, tu entorno,<br>tus reglas.</p>
        </div>
      </article>

      <article class="hero-principle">
        <div class="hero-principle-icon" aria-hidden="true">
          <span>⌘</span>
        </div>

        <div>
          <h2>MODEL<br>AGNOSTIC</h2>
          <p>Funciona con los modelos<br>que elijas.</p>
        </div>
      </article>

      <article class="hero-principle">
        <div class="hero-principle-icon" aria-hidden="true">
          <span>ϟ</span>
        </div>

        <div>
          <h2>AGENTIC<br>QA</h2>
          <p>Agentes autónomos que piensan,<br>analizan y ejecutan.</p>
        </div>
      </article>

      <div class="hero-v2-manifesto">
        MENOS INCERTIDUMBRE.<br>
        MEJORES DECISIONES.<br>
        PRODUCTOS MÁS SEGUROS.
      </div>

    </div>

  </div>
</section>'''

matches = pattern.findall(content)

if len(matches) != 1:
    raise RuntimeError(
        f"Esperaba encontrar exactamente 1 hero; encontré {len(matches)}. "
        "No se modificó index.html."
    )

if 'class="hero hero-v2"' in content:
    raise RuntimeError(
        "El Hero V2 ya existe. No se modificó index.html."
    )

content = pattern.sub(hero, content, count=1)

with path.open("w", encoding="utf-8", newline="") as f:
    f.write(content)

print("OK - HTML HERO V2 agregado")