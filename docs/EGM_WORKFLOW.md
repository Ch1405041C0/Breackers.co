# EGM en Breakers — adopción de diseño y revisión

**Fuente:** [google/elephant-goldfish-model](https://github.com/google/elephant-goldfish-model)  
**Revisión inicial:** 2026-11-10; manifiesto EGM v0.1.1; licencia Apache-2.0.

## Decisión

Adoptar el **Elephant–Goldfish Model (EGM)** como herramienta opcional **para quienes desarrollan Breakers**: un agente con contexto conserva los requisitos y redacta un diseño (*Elephant*), mientras subagentes con contexto conversacional nuevo evalúan el documento y sus referencias (*Goldfish*).

**No** desplegar EGM dentro del contenedor de Breakers, añadirlo a `requirements.txt`, ponerlo en el catálogo de motores o venderlo como capacidad del SCAN. Ninguno de esos cambios forma parte de esta integración documental.

El plugin se instala **en el host del asistente** (Codex/Claude/Antigravity/ChatGPT desktop), no dentro de este repositorio. Esta PR sólo establece la guía y el lugar para los documentos.

## Instalación fuera del proyecto

### Codex CLI

```sh
codex plugin marketplace add google/elephant-goldfish-model
codex plugin add egm@egm
```

### Claude Code

```sh
claude plugin marketplace add google/elephant-goldfish-model
claude plugin install egm@egm
```

### ChatGPT o Codex desktop

Instalar el [plugin publicado de EGM](https://chatgpt.com/plugins/plugins_6aeb90f47ec88191a3c107e01d3eb357) en el **cliente desktop**; este mecanismo no significa que esté instalado en ChatGPT web ni en Work cloud.

Reiniciar la sesión. Verificar que se hayan instalado **skills, personas (`agents/`) y recursos (`resources/`)**. En Codex seleccionar la skill desde el selector; los prefijos de comandos pueden cambiar entre agentes.

## Piloto sugerido: análisis temprano de requerimientos en SCAN

**Pregunta:** ¿Cómo debería SCAN recibir un documento PDF o DOCX, extraer requisitos, registrar evidencia y distinguir inferencias de hallazgos comprobados?

Estado que describe el README actual: `.txt` y `.md` ya admiten análisis preventivo; PDF/DOCX están reconocidos como entradas, pero su extracción está pendiente. Confirmar el estado del código al comenzar el piloto.

1. Leer `docs/BREAKERS_CONSTITUTION.md`, `docs/SCAN_CONTRACT.md`, `breakers/inputs/` y las pruebas pertinentes.
2. Crear un breve `concepts_brief.md` con objetivo, formatos soportados, límites, validaciones, fallos, pruebas y riesgos. Usar `egm-brainstorm` si está disponible.
3. Crear `design_draft.md` con contrato de entrada, normalización, tratamiento de errores, seguridad, trazabilidad y criterios de aceptación; usar `egm-draft`.
4. Invocar `egm-review` con el documento y referencias explícitas. Revisar los hallazgos sobre ambigüedad, cobertura, aislamiento y factibilidad.
5. Resolver prioridades con criterio humano; mover **sólo el diseño aprobado** a `docs/designs/`.
6. Implementar en otra PR, agregar pruebas automatizadas para entradas válidas, corruptas, excesivas, no compatibles y sin texto extraíble; documentar limitaciones de extracción.
7. Ejecutar `egm-drift-report` para contrastar diseño con código después de la implementación.

No hace falta recorrer todas las etapas para fixes pequeños. EGM resulta más útil ante cambios que puedan crear deuda técnica o suposiciones difíciles de detectar.

## Ubicación de artefactos

- `.dev/docs/`: borradores y reportes temporales ignorados por Git.
- `docs/designs/`: diseños revisados y aprobados que deben mantenerse sincronizados con el producto.
- `AGENTS.md`: reglas y localización para agentes.

## Límites importantes

- La independencia Goldfish requiere **subagentes con contexto nuevo**; si el cliente no tiene esa capacidad, no se puede afirmar una revisión aislada.
- La documentación oficial advierte que un contexto nuevo **no garantiza** que los revisores dejen de recibir archivos de instrucciones del host (`AGENTS.md`, `CLAUDE.md`, etc.). Diseños y revisiones siguen necesitando juicio humano.
- EGM no sustituye tests, revisiones de seguridad ni la evidencia que BREAKERS exige.
- Las entradas confidenciales se procesan bajo las reglas del proveedor del asistente; limitar el material compartido.

Referencias: [README original](https://github.com/google/elephant-goldfish-model/blob/main/README.md), [instalación y compatibilidad](https://github.com/google/elephant-goldfish-model/blob/main/docs/harnesses.md), [manejo de datos](https://github.com/google/elephant-goldfish-model/blob/main/docs/privacy.md).
