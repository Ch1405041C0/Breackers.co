# BREAKERS SCAN MVP
1. `pip install -r requirements.txt`
2. Instalar las herramientas que quieras detectar: Trivy, Gitleaks, SonarScanner, ZAP y JMeter.
3. `python app.py`
4. Abrir http://127.0.0.1:8080

El MVP ejecuta Trivy y Gitleaks únicamente contra rutas locales autorizadas. Detecta SonarScanner/ZAP/JMeter, pero sus ejecuciones activas requieren configuración explícita de proyecto, credenciales, alcance y plan de prueba. El frontend consume `/api/scan` y normaliza hallazgos.
