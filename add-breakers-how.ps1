$path = "index.html"

$content = Get-Content $path -Raw -Encoding UTF8

$marker = '<section class="quality-constitution"'

$block = @'
<section class="breakers-how" aria-labelledby="breakers-how-title">
  <div class="wrap">
    <span class="small-label">CÓMO TRABAJA BREAKERS</span>

    <h2 id="breakers-how-title">
      TU CÓDIGO NO VIENE A BREAKERS.<br>
      <strong>BREAKERS VA A TU CÓDIGO.</strong>
    </h2>

    <p class="breakers-how-lead">
      Breakers trabaja sobre el ecosistema que tu equipo ya utiliza.
      Repositorios, aplicaciones, APIs, documentación y evidencia.
    </p>

    <div class="breakers-how-grid">
      <div>
        <span class="mono">01 / PRIVATE BY DESIGN</span>
        <p>Trabajamos donde vive tu producto.</p>
      </div>

      <div>
        <span class="mono">02 / MODEL AGNOSTIC</span>
        <p>El modelo se adapta a tu infraestructura.</p>
      </div>

      <div>
        <span class="mono">03 / AGENTIC QA</span>
        <p>Agentes especializados analizan, proponen y evalúan.</p>
      </div>
    </div>
  </div>
</section>

'@

if (-not $content.Contains($marker)) {
    throw "No encontré quality-constitution. No se modificó index.html."
}

if ($content.Contains('class="breakers-how"')) {
    throw "La sección breakers-how ya existe. No se modificó index.html."
}

$content = $content.Replace($marker, $block + $marker)

Set-Content $path $content -Encoding UTF8

Write-Host "OK - BREAKERS HOW insertado antes de quality-constitution"