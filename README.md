# BREAKERS SCAN MVP

BREAKERS SCAN busca riesgo desde la evidencia disponible en cualquier etapa del producto. Los motores externos son sensores especializados; BREAKERS normaliza y correlaciona sus resultados.

## Probar localmente
1. `git pull` / cambiar a la rama `feature/scan-v0.1` mientras el PR siga abierto.
2. `pip install -r requirements.txt`
3. Opcional: instalar Trivy y Gitleaks para análisis local de repositorios. SonarScanner, ZAP y JMeter se detectan pero requieren configuración explícita para ejecución activa.
4. `python app.py`
5. Abrir `http://127.0.0.1:8080`.

## Primer análisis preventivo
SCAN ya reconoce documentos funcionales `.txt` y `.md` y genera hipótesis de riesgo sobre condiciones, límites y flujos de error. PDF/DOCX están reconocidos como fuentes, pero su extracción todavía está pendiente.

## Motores
El catálogo y estado de integración está en `docs/ENGINE_CATALOG.md`. Regla de UI: toda herramienta adoptada debe aparecer con nombre e identidad visual en el carrusel de motores, sin presentar herramientas catalogadas como si ya estuvieran integradas.

## Seguridad
El MVP sólo ejecuta scanners pasivos contra rutas locales autorizadas. DAST, carga y otros motores activos requieren alcance y configuración explícitos.
