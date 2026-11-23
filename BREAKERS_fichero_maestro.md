# BREAKERS CO — Fichero maestro

Versión 1.0 · 22 de septiembre de 2026

Convertir investigación, observación de competencia y experiencia QA en capacidades propias, oportunidades y decisiones verificables.

**Estado:** Fichero inicial de investigación y diseño. No integrado a un motor ni a una base consultable en ejecución.

## Decisiones vigentes

- Construir soluciones propias de calidad.
- Conservar los tres productos SCAN, STRIKE y CONTROL.
- Usar las referencias para investigar competencia, capacidades, experiencia de usuario, operación y oportunidades.
- Aplicar la exclusión editorial solicitada a esta base y a la página revisada.
- Conservar las técnicas generales de QA de la documentación propia.
- Mantener separación entre conocimiento comprobado, propuesta y funcionalidad implementada.

## Los tres productos

| Producto | Propósito | Entregable principal |
|---|---|---|
| SCAN | Identificar riesgos y huecos de evidencia para decidir dónde investigar primero. | Riesgos priorizados con justificación |
| STRIKE | Transformar riesgos y reglas en un plan de pruebas que pueda ejecutarse. | Casos con precondiciones, pasos y resultado esperado |
| CONTROL | Seguir los resultados entre versiones y explicar si se cumplen los criterios de salida. | Comparación de versiones |

### SCAN

**Estado:** Especificación inicial; motor no implementado en esta entrega.

**Entradas:** Requisitos, flujos o documentación; Alcance y reglas de negocio; Evidencias disponibles y versión.

**Salidas:** Riesgos priorizados con justificación; Preguntas y supuestos diferenciados; Mapa de cobertura y acciones sugeridas.

**Primera versión:**
- Analizar documentación provista
- Vincular afirmaciones con fuentes
- Exportar un diagnóstico estructurado

**Criterios de aceptación:**
- Una afirmación sin respaldo figura como hipótesis.
- Cada riesgo tiene una causa, impacto y referencia o falta de evidencia.
- La falta de información produce preguntas, nunca hallazgos inventados.

### STRIKE

**Estado:** Especificación inicial; motor no implementado en esta entrega.

**Entradas:** Diagnóstico SCAN o riesgos cargados manualmente; Reglas confirmadas; Entorno, datos y restricciones.

**Salidas:** Casos con precondiciones, pasos y resultado esperado; Datos reproducibles y candidatos a automatizar; Trazabilidad y prioridades.

**Primera versión:**
- Diseñar casos y datos desde reglas confirmadas
- Exportar un plan en JSON y formato legible
- Separar casos ejecutables de casos bloqueados por preguntas

**Criterios de aceptación:**
- Cada caso referencia un riesgo o requisito.
- Los casos incluyen negativos y límites pertinentes.
- Un resultado esperado desconocido se marca pendiente; no se inventa.

### CONTROL

**Estado:** Especificación inicial; motor no implementado en esta entrega.

**Entradas:** Plan de pruebas versionado; Resultados y evidencias de ejecución; Reglas de salida y baseline.

**Salidas:** Comparación de versiones; Fallos, bloqueos y faltantes identificados; Decisión explicada y paquete de evidencias.

**Primera versión:**
- Importar resultados en un formato común
- Validar asociación a caso, entorno y versión
- Aplicar reglas de salida sin ocultar fallos críticos

**Criterios de aceptación:**
- Evidencia ausente produce no verificable.
- El resultado identifica la regla incumplida.
- Un fallo crítico no desaparece en una media global.
- No confundir un error del ejecutor con un fallo confirmado del producto.

## Competencia y oportunidades

Las siguientes son hipótesis de diferenciación. La revisión de sitios públicos no demuestra exclusividad ni superioridad de BREAKERS.

| Referencia | Qué estudiar | Hipótesis para BREAKERS |
|---|---|---|
| QAlified / evaluación de IA | Combinación de servicios y herramientas propias. | Conectar riesgo, reglas, datos y evidencia de una misma versión, con revisión en español. |
| Sauce Labs | Cobertura de plataformas, diagnóstico y automatización asistida. | Priorización de cobertura por riesgo y explicaciones útiles para equipos pequeños. |
| bitegarden | Transformación de resultados técnicos en informes y decisiones. | Unir evidencias de distintas capas y evitar decisiones basadas solo en un informe. |

Validación propuesta: usar un caso sintético común, medir omisiones, reproducibilidad, tiempo de revisión y claridad del resultado. Registrar también dónde otra solución resuelve mejor el problema.

## Registro de referencias

### F01 · ZAP

**Usos:** capacidad_tecnica, automatizacion. **Productos:** SCAN, CONTROL.

**Observado:** La documentación presenta opciones de automatización de pruebas de seguridad web y un Automation Framework con planes y trabajos.

**Aplicación propuesta:** Definir trabajos de seguridad repetibles y convertir sus hallazgos en evidencias vinculadas a una versión del sistema.

**Por validar:** Autenticación, alcance autorizado, falsos positivos y recursos necesarios para cada aplicación.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://www.zaproxy.org/](https://www.zaproxy.org/)
- [https://www.zaproxy.org/docs/automate/](https://www.zaproxy.org/docs/automate/)
### F02 · Alias de Gmail

**Usos:** datos_de_prueba, analisis_critico. **Productos:** STRIKE.

**Observado:** Los alias con etiquetas permiten dirigir mensajes al mismo buzón; no crean cuentas de Google independientes.

**Aplicación propuesta:** Diseñar pruebas de registro, duplicados y recuperación con correlación por escenario.

**Por validar:** Reglas de normalización del sistema y si acepta etiquetas; usar cuentas y buzones de prueba controlados.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://distritodigital.biz/como-crear-infinitas-cuentas-de-correo-con-gmail/](https://distritodigital.biz/como-crear-infinitas-cuentas-de-correo-con-gmail/)
### F03 · Ethereum Waffle

**Usos:** capacidad_tecnica, reproducibilidad. **Productos:** STRIKE, CONTROL.

**Observado:** La documentación explica proveedores de prueba y operaciones con contratos; también se consultaron fixtures, mocks y aserciones.

**Aplicación propuesta:** Aplicar el patrón preparar actores y datos, ejecutar, verificar y restaurar el estado. Integración EVM solo para ese dominio.

**Por validar:** Compatibilidad y mantenimiento de versiones antes de seleccionar esta dependencia.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://ethereum-waffle.readthedocs.io/en/latest/basic-testing.html#creating-a-provider](https://ethereum-waffle.readthedocs.io/en/latest/basic-testing.html#creating-a-provider)
### F04 · Temp Mail

**Usos:** datos_de_prueba, capacidad_tecnica. **Productos:** STRIKE.

**Observado:** El sitio ofrece correo temporal y documentación de API; la disponibilidad de mensajes tiene límites temporales.

**Aplicación propuesta:** Diseñar un adaptador intercambiable para probar recepción y expiración de mensajes.

**Por validar:** Cuotas, duración, restricciones y acceso al proveedor; no considerar permanente un buzón temporal.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://temp-mail.org/es/](https://temp-mail.org/es/)
### F05 · SonarQube: artículo de instalación

**Usos:** capacidad_tecnica, analisis_critico. **Productos:** SCAN, CONTROL.

**Observado:** El artículo usa versiones antiguas. Se contrastaron aspectos de configuración, cobertura y quality gates con documentación oficial durante la revisión.

**Aplicación propuesta:** Relacionar problemas de código, exclusiones y reglas con evidencia de cada revisión y con pruebas de comportamiento.

**Por validar:** Revalidar instalación, nombres de parámetros y compatibilidad en la documentación de la versión elegida.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://www.c-sharpcorner.com/article/step-by-step-sonarqube-setup-and-run-sonarqube-scanner](https://www.c-sharpcorner.com/article/step-by-step-sonarqube-setup-and-run-sonarqube-scanner)
### F06 · JMeter

**Usos:** capacidad_tecnica, automatizacion. **Productos:** SCAN, STRIKE, CONTROL.

**Observado:** El artículo introduce planes de carga. La revisión distinguió usuarios concurrentes, ramp-up y throughput, y contrastó la ejecución sin interfaz para carga con Apache.

**Aplicación propuesta:** Construir escenarios de rendimiento con datos, pausas, aserciones, métricas y umbrales definidos por negocio.

**Por validar:** Volumen real, entorno, capacidad del generador, monitoreo y límites aceptables del producto.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://somospnt.com/blog/91-load-testing-con-jmeter](https://somospnt.com/blog/91-load-testing-con-jmeter)
- [https://jmeter.apache.org/download_jmeter.cgi](https://jmeter.apache.org/download_jmeter.cgi)
### F07 · WeTransfer

**Usos:** operacion, entrega_de_evidencia. **Productos:** CONTROL.

**Observado:** Es una referencia de experiencia de envío de archivos mediante enlaces o correo; se consultó ayuda pública porque la portada no se pudo leer completamente.

**Aplicación propuesta:** Diseñar entregas simples de evidencia con vencimiento visible y un registro permanente independiente.

**Por validar:** Necesidades de retención, acceso y trazabilidad; no equivale a un repositorio de resultados.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://wetransfer.com/](https://wetransfer.com/)
### F08 · bitegarden

**Usos:** competencia_adyacente, reportes, oportunidad. **Productos:** SCAN, CONTROL.

**Observado:** Presenta productos que amplían reportes, análisis de seguridad y administración alrededor de SonarQube.

**Aplicación propuesta:** Estudiar cómo convierte resultados técnicos en informes útiles; diferenciar BREAKERS con trazabilidad y decisiones entre fuentes.

**Por validar:** Valor de esa diferencia mediante casos reales. Las capacidades comerciales no se probaron en una cuenta.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://www.bitegarden.com/](https://www.bitegarden.com/)
### F09 · LatinCloud

**Usos:** infraestructura, operacion. **Productos:** CONTROL.

**Observado:** Se consultaron páginas públicas de infraestructura y VPS; la portada tuvo problemas de acceso durante la revisión.

**Aplicación propuesta:** Definir requisitos de ejecución aislada, respaldo y observabilidad que puedan implementarse sobre distintos entornos.

**Por validar:** Arquitectura y recursos de BREAKERS; ninguna elección de proveedor ni contratación está decidida.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://latincloud.com/](https://latincloud.com/)
### F10 · Lucid

**Usos:** experiencia_de_usuario, modelado, oportunidad. **Productos:** SCAN, STRIKE.

**Observado:** Presenta herramientas de diagramación, colaboración y planificación.

**Aplicación propuesta:** Conectar visualmente reglas, flujos, riesgos y pruebas para ayudar a comprender cobertura y dependencias.

**Por validar:** Qué representación mejora realmente las decisiones de un QA y si conviene generarla dentro de BREAKERS.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://lucid.co/](https://lucid.co/)
### F11 · Twilio

**Usos:** capacidad_tecnica, datos_de_prueba. **Productos:** STRIKE, CONTROL.

**Observado:** Ofrece capacidades de comunicación y verificación. Los mecanismos de prueba consultados no simulan universalmente todos los productos ni callbacks.

**Aplicación propuesta:** Modelar OTP, reintentos, expiración, duplicados y entrega como estados de una comunicación.

**Por validar:** Contrato y comportamiento del canal específico; distinguir simulación de entrega real.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://www.twilio.com/es-mx](https://www.twilio.com/es-mx)
### F12 · VIN Generator

**Usos:** datos_de_prueba. **Productos:** STRIKE.

**Observado:** El sitio genera ejemplos de VIN con opciones de vehículo. No se confirmó una API ni exclusividad de los identificadores generados.

**Aplicación propuesta:** Mantener conjuntos reproducibles de datos válidos e inválidos con resultado esperado.

**Por validar:** Reglas del dominio y colisiones; un valor generado no prueba que un vehículo exista o que sea completamente ficticio.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://vingenerator.org/](https://vingenerator.org/)
### F13 · Sauce Labs

**Usos:** competencia, compatibilidad, oportunidad. **Productos:** SCAN, STRIKE, CONTROL.

**Observado:** Presenta ejecución en navegadores y dispositivos y capacidades de automatización asistida por IA. Se revisó su oferta pública, sin prueba práctica del servicio.

**Aplicación propuesta:** Investigar cobertura de plataformas, diagnóstico y evidencia de fallos; evaluar qué puede resolver BREAKERS con su propia arquitectura.

**Por validar:** Rendimiento y calidad reales de las funciones anunciadas. La oferta comercial no demuestra ventaja exclusiva de BREAKERS.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://saucelabs.com/](https://saucelabs.com/)
### F14 · Hacker Highschool

**Usos:** formacion_tecnica, seguridad. **Productos:** SCAN, STRIKE.

**Observado:** El índice reúne lecciones de redes, sistemas, seguridad y análisis forense.

**Aplicación propuesta:** Identificar temas para elaborar guías propias de investigación y preguntas de diagnóstico.

**Por validar:** Lectura de lecciones individuales y condiciones de reutilización antes de incorporar contenido completo.

**Alcance:** Se revisó el índice de lecciones; no se leyeron todos los manuales.

**Rutas:**
- [https://www.hackerhighschool.org/lessons.html](https://www.hackerhighschool.org/lessons.html)
### F15 · QAlified: pruebas de API

**Usos:** capacidad_tecnica, competencia, analisis. **Productos:** STRIKE, CONTROL.

**Observado:** El artículo presenta pruebas con Postman. La revisión destacó colecciones, scripts y validación de comportamiento; un HTTP 200 no demuestra una regla de negocio.

**Aplicación propuesta:** Diseñar aserciones de contrato, permisos, estados e integridad de datos para cada operación.

**Por validar:** Formato de colecciones y ejecutor compatibles con el proyecto antes de integrar una herramienta concreta.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://qalified.com/es/blog/postman-para-api-testing/](https://qalified.com/es/blog/postman-para-api-testing/)
### F16 · QAlified: testing e IA

**Usos:** competencia, posicionamiento, oportunidad. **Productos:** SCAN, STRIKE, CONTROL.

**Observado:** La oferta pública distingue probar sistemas de IA y utilizar IA en testing; presenta además una herramienta propia de evaluación.

**Aplicación propuesta:** Definir resultados verificables y un flujo de revisión humana para la automatización asistida.

**Por validar:** Capacidades reales, calidad y límites mediante casos comparables; no se utilizó el producto competidor.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://qalified.com/es/ia-testing/](https://qalified.com/es/ia-testing/)
### F17 · QAlified: evaluación de LLM

**Usos:** competencia, capacidad_tecnica, oportunidad. **Productos:** SCAN, STRIKE, CONTROL.

**Observado:** Se revisaron estrategias de conjuntos de evaluación, regresión, RAG y jueces. Las categorías y afirmaciones sobre herramientas requirieron contraste con documentación primaria.

**Aplicación propuesta:** Separar reglas determinísticas de evaluaciones por modelo, calibrar contra revisores humanos y conservar cada configuración.

**Por validar:** Confiabilidad de cada métrica, variabilidad y cobertura del dominio; una nota global no reemplaza revisar fallos críticos.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://qalified.com/es/blog/mejores-herramientas-evaluacion-llm/](https://qalified.com/es/blog/mejores-herramientas-evaluacion-llm/)
- [https://qalified.com/es/blog/estrategias-testing-llm/](https://qalified.com/es/blog/estrategias-testing-llm/)
### F18 · Drimcom

**Usos:** mercado, posicionamiento. **Productos:** Investigación empresarial.

**Observado:** Las páginas consultadas presentan acompañamiento estratégico a empresas. El acceso directo a la portada fue incompleto.

**Aplicación propuesta:** Estudiar cómo traducir problemas técnicos a necesidades del negocio y segmentar clientes.

**Por validar:** Encaje concreto para BREAKERS. No se lo clasifica como competidor técnico directo por esta revisión.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://drimcom.com.ar/](https://drimcom.com.ar/)
### F19 · Agencia SINC

**Usos:** investigacion, vigilancia_tecnologica. **Productos:** Investigación empresarial.

**Observado:** Es una fuente de noticias científicas; no se seleccionó en esta conversación un estudio específico para implementar.

**Aplicación propuesta:** Usar noticias como punto de entrada a investigaciones originales que puedan mejorar la evaluación de sistemas.

**Por validar:** Métodos, datos y limitaciones de cada trabajo primario antes de convertir una noticia en capacidad de producto.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://www.agenciasinc.es/](https://www.agenciasinc.es/)
### F20 · Overemployed

**Usos:** mercado, contexto_laboral. **Productos:** Investigación empresarial.

**Observado:** El sitio aborda trabajo remoto y simultaneidad de empleos. No aporta por sí mismo una técnica de calidad de software.

**Aplicación propuesta:** Conservar como referencia secundaria sobre organización del trabajo; su utilidad comercial para BREAKERS es una hipótesis.

**Por validar:** No priorizar desarrollo a partir de esta referencia sin identificar un problema concreto de cliente.

**Alcance:** Página o documentación consultada durante esta conversación; revisión selectiva, no exhaustiva.

**Rutas:**
- [https://overemployed.com/](https://overemployed.com/)
### F21 · Caso de gestión de stock compartido en la conversación

**Usos:** caso_de_estudio, reglas_de_negocio. **Productos:** SCAN, STRIKE, CONTROL.

**Observado:** Se observó una pantalla administrativa con listado de productos, precios y stock. La observación fue de lectura.

**Aplicación propuesta:** Preparar un caso propio, con datos sintéticos, sobre consistencia de stock, precios, permisos y operaciones repetidas.

**Por validar:** Reglas funcionales, entorno y alcance antes de ejecutar pruebas. El acceso visual no demuestra seguridad ni vulnerabilidades.

**Alcance:** Observación limitada al listado; no se almacenan dirección de acceso, credenciales ni datos de terceros en este fichero.
### F22 · Documentación propia de QA Agent

**Usos:** conocimiento_propio, arquitectura, metodologia. **Productos:** SCAN, STRIKE, CONTROL.

**Observado:** Se leyeron los siete documentos del proyecto sobre visión, cobertura, casos, patrones, arquitectura, automatización y roadmap.

**Aplicación propuesta:** Usarlos como continuidad de diseño: preguntas y supuestos explícitos, trazabilidad y revisión crítica de los resultados.

**Por validar:** Las etapas del roadmap describen una propuesta; no acreditan que los motores o conectores estén implementados.

**Alcance:** Lectura del contenido de los siete documentos 01 a 07 de QA Agent / Conversaciones Convertidas.

## Fichas de problemas de calidad

### P01 · Requisitos incompletos producen huecos de cobertura

**Productos:** SCAN, STRIKE. **Fuentes:** F22.

**Estado:** diseño; no ejecutado.

**Causas a investigar:** Reglas implícitas; Estados o perfiles sin describir.

**Cómo investigar:**
1. Identificar reglas, actores y estados con su ubicación en la fuente.
2. Separar requisitos confirmados, hipótesis y preguntas.
3. Relacionar cada riesgo con escenarios de prueba.

**Evidencia:** Referencia al requisito; Preguntas abiertas; Mapa de riesgo y cobertura.

**Corrección y reprueba:** Confirmar reglas con el responsable del producto y regenerar solo los casos afectados.

**Límite:** La ausencia de un requisito impide decidir el resultado esperado; registrar no verificable.
### P02 · Una API responde correctamente pero incumple la regla de negocio

**Productos:** SCAN, STRIKE, CONTROL. **Fuentes:** F15, F22.

**Estado:** diseño; no ejecutado.

**Causas a investigar:** Aserciones limitadas al código HTTP; Permisos o persistencia no revisados.

**Cómo investigar:**
1. Definir resultado de negocio, contrato y permisos.
2. Ejecutar escenarios positivos, negativos, repetidos y con distintos perfiles.
3. Comprobar estado final en las fuentes autorizadas.

**Evidencia:** Request y response anonimizados; Aserciones y resultado de negocio; Datos antes y después cuando corresponda.

**Corrección y reprueba:** Corregir contrato o lógica y repetir el caso más la regresión de operaciones relacionadas.

**Límite:** No inferir datos internos ni permisos no provistos; un transporte exitoso no certifica una operación.
### P03 · La aplicación se degrada bajo concurrencia

**Productos:** SCAN, STRIKE, CONTROL. **Fuentes:** F06.

**Estado:** diseño; no ejecutado.

**Causas a investigar:** Saturación de servicios o base de datos; Datos o pausas irreales; Generador de carga insuficiente.

**Cómo investigar:**
1. Definir mezcla de operaciones y objetivos acordados.
2. Preparar entorno y datos, aumentar carga gradualmente y registrar métricas.
3. Correlacionar latencia y errores con recursos del sistema y del generador.

**Evidencia:** Plan y configuración; p95/p99, throughput y errores; Monitoreo de ambas partes y versión del sistema.

**Corrección y reprueba:** Identificar el cuello de botella, corregir y comparar bajo el mismo escenario.

**Límite:** No convertir usuarios concurrentes en RPS sin medición ni fijar umbrales universales.
### P04 · Un resultado de seguridad se interpreta sin contexto

**Productos:** SCAN, CONTROL. **Fuentes:** F01, F05, F14.

**Estado:** diseño; no ejecutado.

**Causas a investigar:** Cobertura incompleta; Exclusiones desconocidas; Hallazgos sin validación.

**Cómo investigar:**
1. Definir activos, alcance, credenciales de prueba y reglas.
2. Distinguir análisis de código de observaciones de ejecución.
3. Revisar cada hallazgo relevante y registrar evidencia reproducible.

**Evidencia:** Herramienta y versión; Reglas y exclusiones; Evidencia y estado de revisión.

**Corrección y reprueba:** Corregir causas confirmadas y volver a comprobar el escenario y su regresión.

**Límite:** Un gate verde o un acceso exitoso no demuestran seguridad completa. Las pruebas activas necesitan alcance definido.
### P05 · Correos o códigos de verificación generan pruebas inestables

**Productos:** STRIKE, CONTROL. **Fuentes:** F02, F04, F11.

**Estado:** diseño; no ejecutado.

**Causas a investigar:** Mensajes confundidos entre casos; Expiración o retrasos; Normalización de identidad no definida.

**Cómo investigar:**
1. Usar identificadores de correlación por caso.
2. Modelar espera, reintento, entrega y vencimiento.
3. Verificar duplicados e identidad según las reglas del sistema.

**Evidencia:** ID de correlación; Tiempos y estados; Resultado esperado de expiración y reintento.

**Corrección y reprueba:** Aislar datos y corregir manejo de estados; repetir también los errores de canal.

**Límite:** Un alias no constituye un usuario independiente. Los simuladores de comunicación tienen un alcance específico.
### P06 · Una prueba no puede reproducirse

**Productos:** STRIKE, CONTROL. **Fuentes:** F03, F12.

**Estado:** diseño; no ejecutado.

**Causas a investigar:** Datos aleatorios no guardados; Estado compartido; Dependencias variables.

**Cómo investigar:**
1. Guardar semilla o conjunto de datos y configuración.
2. Preparar precondiciones y aislar dependencias.
3. Restablecer el estado y repetir la ejecución.

**Evidencia:** Dataset versionado; Precondiciones; Procedimiento de restauración.

**Corrección y reprueba:** Eliminar dependencias accidentales y comprobar que el mismo escenario obtiene un resultado comparable.

**Límite:** El patrón es general; las funciones específicas de Waffle aplican a su entorno EVM.
### P07 · Una mejora del modelo introduce regresiones en IA

**Productos:** SCAN, STRIKE, CONTROL. **Fuentes:** F16, F17.

**Estado:** diseño; no ejecutado.

**Causas a investigar:** Dataset poco representativo; Jueces sin calibrar; Cambio de modelo, prompt o recuperación.

**Cómo investigar:**
1. Versionar ejemplos, prompt, modelo y configuración.
2. Aplicar primero las reglas que tengan un resultado determinístico.
3. Evaluar lo variable con métricas explícitas, revisión humana y repeticiones justificadas.

**Evidencia:** Resultados por caso; Configuración y baseline; Discrepancias con revisión humana.

**Corrección y reprueba:** Corregir la causa específica y reevaluar el conjunto representativo, incluyendo los fallos críticos.

**Límite:** Una media alta puede ocultar casos graves. No afirmar precisión absoluta a partir de un juez de modelo.
### P08 · Una entrega se aprueba sin evidencia suficiente

**Productos:** CONTROL. **Fuentes:** F05, F08, F22.

**Estado:** diseño; no ejecutado.

**Causas a investigar:** Resultados ausentes o antiguos; Reglas de salida implícitas; Versiones mezcladas.

**Cómo investigar:**
1. Vincular cada resultado a versión, entorno y caso.
2. Aplicar reglas de aceptación explícitas.
3. Mostrar fallos, bloqueos y datos faltantes con sus razones.

**Evidencia:** Run ID; Versión y entorno; Decisión explicada por regla.

**Corrección y reprueba:** Completar o repetir evidencia faltante antes de reevaluar la entrega.

**Límite:** Cero resultados no equivale a aprobado; no promediar un fallo crítico hasta ocultarlo.
### P09 · Un flujo funciona solo en algunas plataformas

**Productos:** SCAN, STRIKE, CONTROL. **Fuentes:** F13.

**Estado:** diseño; no ejecutado.

**Causas a investigar:** Matriz de dispositivos incompleta; Diferencias de navegador, permisos o resolución.

**Cómo investigar:**
1. Priorizar plataformas por uso y riesgo.
2. Ejecutar el mismo flujo con datos controlados.
3. Separar problemas de aplicación, entorno y automatización.

**Evidencia:** Plataforma y versión; Pasos y datos; Captura o log de reproducción.

**Corrección y reprueba:** Corregir la incompatibilidad y repetir las combinaciones afectadas.

**Límite:** Una ejecución de escritorio no acredita comportamiento móvil ni cobertura de todos los dispositivos.
### P10 · Stock o precios inconsistentes después de una operación

**Productos:** SCAN, STRIKE, CONTROL. **Fuentes:** F21, F22.

**Estado:** diseño; no ejecutado.

**Causas a investigar:** Actualizaciones parciales; Operación duplicada; Permisos o redondeos incorrectos.

**Cómo investigar:**
1. Confirmar reglas de venta, reserva, devolución y precios.
2. Diseñar límites y transiciones con datos sintéticos.
3. Comparar estados antes y después, incluyendo reintentos y operaciones concurrentes cuando estén autorizadas.

**Evidencia:** Reglas confirmadas; Estado inicial y final; Identificador de operación y permisos usados.

**Corrección y reprueba:** Corregir atomicidad, validación o estado y repetir el escenario más los flujos relacionados.

**Límite:** Es un caso de diseño: no se ejecutaron ventas, cambios de stock ni pruebas intrusivas en el sistema observado.

## Backlog de desarrollo

Todos los ítems siguientes están pendientes. P0 construye el recorrido mínimo común; P1 conecta operación y publicación; P2 amplía capacidades.

| ID | Prioridad | Producto | Trabajo | Aceptación |
|---|---|---|---|---|
| CORE-01 | P0 | Común | Definir contrato de requisito, riesgo, caso, ejecución y evidencia. | IDs estables, versión y estado de verificación en cada entidad. |
| CORE-02 | P0 | Común | Construir consulta de fichas por problema y producto. | Devuelve referencias y distingue observación de propuesta. |
| SCAN-01 | P0 | SCAN | Extraer reglas y preguntas de un documento de ejemplo. | Ninguna regla confirmada carece de fuente; vacíos explícitos. |
| SCAN-02 | P0 | SCAN | Priorizar riesgos con factores visibles. | El usuario puede revisar impacto, probabilidad y justificación. |
| STRIKE-01 | P0 | STRIKE | Convertir un riesgo en casos ejecutables. | Pasos, datos, precondiciones, resultado y vínculo presentes. |
| STRIKE-02 | P0 | STRIKE | Exportar plan y conjunto de datos. | El archivo permite reconstruir el mismo escenario. |
| CONTROL-01 | P0 | CONTROL | Importar resultados y validar integridad. | Rechaza IDs desconocidos y versiones incompatibles con motivo. |
| CONTROL-02 | P0 | CONTROL | Aplicar reglas de salida. | Un caso crítico fallido bloquea y uno sin evidencia queda no verificable. |
| E2E-01 | P0 | Común | Probar el recorrido de los tres productos con un caso sintético de stock. | Requisito, riesgo, caso y resultado quedan conectados; no usa el sistema externo. |
| WEB-01 | P1 | Página | Conectar un canal real para recibir consultas. | Validación, envío comprobado y confirmación solo tras éxito. |
| WEB-02 | P1 | Página | Publicar la versión revisada en el sitio existente. | Dominio y proyecto de despliegue identificados; versión publicada comprobada. |
| CONNECT-01 | P1 | Común | Elegir el primer conector después de validar el flujo común. | Selección por problema demostrado, con alcance y versión compatibles. |
| AI-01 | P2 | Común | Añadir evaluación de sistemas de IA. | Dataset, configuración, métricas y revisión humana versionados. |

## Página revisada

- Contenido centrado en resultados y alcance de SCAN, STRIKE y CONTROL.
- Retiro del manifiesto y las menciones solicitadas.
- Nombre unificado como BREAKERS CO.
- Ejemplos identificados como demostraciones.
- Retiro de cifras de ahorro, garantías y promesas absolutas sin evidencia.
- HTML autónomo con estilos y lógica incluidos.
- Preparación y descarga local de un resumen; no simula envío de consultas.

## Estado y alcance de la entrega

- Se actualiza el HTML identificado en los archivos; no se ha publicado en un dominio.
- No se dispone de los motores de los tres productos para modificarlos en esta entrega.
- Los nuevos documentos son una especificación y una base de investigación.
- La revisión de referencias externas fue selectiva; no comprende todos los documentos enlazados.
- La búsqueda textual revisó la página, siete documentos de QA, tres PDFs de fundamentos y dos archivos de casos; no inspeccionó imágenes ni el contenido de los ZIP históricos.

## Verificación

- JSON válido; IDs de fuentes y referencias de fichas consistentes.
- Página revisada mediante análisis estático: sintaxis JavaScript, IDs, enlaces internos, etiquetas de formulario y relación de pestañas.
- No se completó la prueba visual ni interactiva: el navegador disponible bloqueó la apertura del archivo local.
- La navegación, el formulario y la descarga requieren una prueba de aceptación en un navegador habilitado antes de publicar.

## Uso del fichero

La versión JSON contiene los mismos datos organizados en fuentes, fichas, productos y backlog. Cada nueva referencia debe incluir alcance de lectura y distinguir lo observado de su posible aplicación. Un consumidor futuro deberá usar esos estados y citar las fuentes; este archivo por sí solo no entrena ni conecta un modelo.

**Siguiente hito:** Implementar CORE-01, SCAN-01, STRIKE-01 y CONTROL-01/02 sobre un caso sintético compartido.
