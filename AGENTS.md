# Breakers — reglas para agentes de desarrollo

EGM artifact directory: .dev/docs

## Contexto de producto

Leer `docs/BREAKERS_CONSTITUTION.md` antes de formular o revisar diseños. BREAKERS es una plataforma de **calidad y riesgo**, no solo un ejecutor de testing. Sus productos: SCAN (descubrimiento de riesgos), STRIKE (profundización y validación) y CONTROL (seguimiento, aún conceptual).

Leer `docs/SCAN_CONTRACT.md` para diseñar cambios en SCAN, y `docs/ENGINE_CATALOG.md` antes de proponer motores.

## Cómo usar EGM

- EGM es una **herramienta del proceso de desarrollo**, no una dependencia del servidor de Breakers ni un motor de análisis disponible para clientes.
- Ver `docs/EGM_WORKFLOW.md` para instalación y primer caso piloto.
- Escribir borradores y hallazgos en `.dev/docs/`; versionar diseños acordados en `docs/designs/`.
- Revisar especificaciones antes de cambios importantes en contratos de entrada, pipeline, scoring, seguridad y reportes.
- No afirmar que se ejecutó una revisión Goldfish aislada cuando el entorno no ofrece subagentes con contexto nuevo.
- Mantener la distinción `detectado / comprobado / inferido / recomendado para validación`. No promover hipótesis a hechos ni atribuir severidad sin evidencia.

## Límites de seguridad y verificación

- No ejecutar escaneos activos, cargas, DAST o análisis sobre terceros sin alcance explícitamente autorizado.
- No exponer secretos, datos de clientes, tokens ni archivos privados a agentes.
- No alterar el runtime de SCAN/STRIKE, sus dependencias o la CI sin un cambio técnico específico y sus pruebas.
- Ejecutar pruebas pertinentes y revisión humana antes de unir cambios funcionales.
- No interpretar un informe EGM como sustituto de las pruebas de Breakers.
