# BREAKERS SCAN MVP

BREAKERS SCAN orquesta distintas fuentes de evidencia y normaliza los hallazgos en un Quality Brief.

## Stack
- Trivy: vulnerabilidades, configuración y secretos
- Gitleaks: secretos
- Semgrep: análisis estático
- SonarQube Community / SonarScanner: calidad y SAST
- OWASP ZAP: DAST web/API
- Apache JMeter: performance
- Newman: pruebas de API
- Playwright: E2E
- Lighthouse y axe-core: calidad web y accesibilidad (integración planificada)

## Desarrollo
1. Instalar Docker Desktop.
2. Copiar `.env.example` a `.env` y completar solo las credenciales necesarias.
3. Levantar el stack con `docker compose up --build`.
4. Abrir BREAKERS en el puerto 8080 y SonarQube en el 9000.

El endpoint `/api/tools` informa qué motores están disponibles. `/api/scan` ejecuta adaptadores locales seguros para Trivy, Gitleaks y Semgrep y puede importar hallazgos de SonarQube cuando está configurado.

Las pruebas activas DAST y de carga no se disparan automáticamente: requieren objetivo, alcance y autorización explícitos.
