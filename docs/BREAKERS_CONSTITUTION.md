# Constitución de Breakers

## 1. Qué es Breakers

**Breakers es una plataforma de análisis de calidad y riesgo para proyectos digitales.**

Puede intervenir en cualquier momento de un proyecto.

No necesita esperar a que exista código.  
No necesita esperar a que exista una aplicación terminada.  
No necesita esperar a QA.  
No necesita esperar a producción.

**Si existe algo que pueda ser analizado, existe una oportunidad de encontrar riesgos.**

Un requerimiento, una historia de usuario, un documento funcional, un diseño, una interfaz, una API, un repositorio, una aplicación, un sitio o evidencia de testing pueden contener problemas mucho antes de convertirse en un defecto en producción.

La función de Breakers es encontrarlos.

---

## 2. La calidad no empieza en QA

Este me parece **el corazón conceptual de la empresa**.

Tradicionalmente pensamos:

**Análisis → Diseño → Desarrollo → QA → Producción**

y muchas veces calidad aparece cerca del final.

Breakers parte de otra idea:

> **La calidad existe durante todo el proyecto.**

Una ambigüedad en un requerimiento es un riesgo de calidad.

Una navegación confusa es un riesgo de calidad.

Una inconsistencia de UX es un riesgo de calidad.

Una decisión de arquitectura puede introducir un riesgo.

Una API mal definida puede introducir un riesgo.

Una dependencia vulnerable es un riesgo.

Un secreto expuesto es un riesgo.

Un problema de accesibilidad es un riesgo.

Una degradación de performance es un riesgo.

Un bug funcional es un riesgo.

**No esperamos que el problema llegue a QA para empezar a buscarlo.**

---

## 3. Breakers analiza lo que existe hoy

Breakers no exige que un proyecto tenga determinada madurez.

Podés llegar con:

**ANÁLISIS Y DEFINICIÓN**

Requerimientos, historias de usuario, criterios de aceptación, documentación funcional, reglas de negocio, especificaciones.

**UX / UI**

Wireframes, mockups, capturas, flujos, interfaces y diseños.

**ARQUITECTURA Y DESARROLLO**

Repositorios, código, dependencias, configuraciones y documentación técnica.

**APIs**

Contratos, especificaciones, endpoints y comportamiento.

**APLICACIONES**

Web, APK, IPA y otros artefactos ejecutables soportados.

**QA**

Casos de prueba, evidencias, resultados, documentación y otros artefactos del proceso de calidad.

Cada entrada es diferente.

Por eso **Breakers no aplica siempre el mismo análisis**.

---

## 4. El usuario no necesita saber qué herramienta usar

Este es otro principio central.

El cliente no debería necesitar conocer:

- qué scanner utilizar;
- qué framework elegir;
- qué reglas ejecutar;
- qué herramienta sirve para cada artefacto.

Eso es responsabilidad de Breakers.

El usuario entrega el objetivo.

Breakers:

**identifica → comprende → decide → analiza → contrasta → normaliza → prioriza → explica.**

Las herramientas son infraestructura interna.

**El producto es la respuesta.**

---

## 5. Breakers no entrega ruido

Diecisiete herramientas produciendo diecisiete reportes no equivalen a conocimiento.

Breakers debe transformar resultados técnicos, reglas y análisis diferentes en un lenguaje común:

> **Hallazgo → ubicación → evidencia → riesgo → prioridad → acción recomendada**

Cuando diferentes mecanismos detecten manifestaciones del mismo problema, Breakers debe intentar consolidarlas.

El objetivo no es entregar la mayor cantidad posible de alertas.

El objetivo es responder:

**¿Qué encontramos?**  
**¿Dónde está?**  
**¿Qué evidencia tenemos?**  
**¿Por qué importa?**  
**¿Qué debería atenderse primero?**  
**¿Qué conviene hacer ahora?**

---

## 6. Breakers trabaja sobre riesgo, no sólo sobre bugs

Esto nos separa mucho de un tester automático.

Un problema no necesita haberse convertido todavía en un bug para ser relevante.

Breakers busca **riesgos de calidad**.

Eso puede incluir riesgos:

**funcionales · técnicos · seguridad · UX/UI · accesibilidad · performance · mantenibilidad · integración · datos · definición · arquitectura · operación**

según el artefacto disponible y aquello que pueda comprobarse razonablemente.

No todas esas dimensiones aplican siempre.

**Breakers debe decidir cuáles tienen sentido para lo que recibió.**

---

## 7. La evidencia manda

Breakers no debería presentar una sospecha como un hecho.

Cada hallazgo debe distinguir entre lo que fue:

**detectado, comprobado, inferido o recomendado para validación.**

Cuanto mayor sea la severidad atribuida a algo, mayor importancia tiene poder explicar por qué.

La confianza del producto no nace de decir:

> “Encontramos algo crítico.”

Nace de poder responder:

> “Encontramos esto, acá está la evidencia y ésta es la razón por la que importa.”

---

## 8. Los tres productos

Y acá finalmente encaja perfecto la arquitectura.

### SCAN — Descubrir

**Encontrá los riesgos antes de que se conviertan en problemas.**

SCAN recibe lo que existe hoy del proyecto, identifica qué puede analizarse y busca riesgos automáticamente.

No requiere que el usuario conozca las herramientas.

Su misión es:

**descubrir, ordenar y priorizar.**

### STRIKE — Profundizar

Acá no quiero definirlo todavía por vos porque dijiste que tenés una idea específica y quiero escucharla.

Por ahora sólo conservaría:

> **SCAN descubre. STRIKE profundiza y valida.**

Y construimos su Constitución cuando me expliques exactamente qué querés que haga.

### CONTROL — Mantener

Tampoco lo encerraría todavía en una definición demasiado técnica.

La idea madre:

> **CONTROL mantiene la calidad bajo observación a medida que el proyecto cambia.**

---

# La versión que pondría en la web

La Constitución completa nos sirve internamente. **No pondría semejante pared de texto en la home.**

Haría una sección nueva después de “Nuestro enfoque”, por ejemplo:

## La calidad no empieza en QA

> **No necesitás tener un producto terminado para encontrar riesgos.**
>
> Breakers puede analizar un proyecto desde sus primeras definiciones hasta producción.
>
> Requerimientos. Diseños. UX/UI. APIs. Código. Repositorios. Aplicaciones. Evidencia de QA.
>
> Nos das lo que existe hoy.  
> **Breakers identifica qué es, decide cómo analizarlo y encuentra qué merece atención.**

Y visualmente debajo:

```text
ANÁLISIS        UX / UI        DESARROLLO        QA        PRODUCCIÓN
    \              |               |              |             /
     \             |               |              |            /
      ────────────────→  BREAKERS  ←────────────────
                              │
                              ↓
                         IDENTIFICA
                              ↓
                           ANALIZA
                              ↓
                       ENCUENTRA RIESGOS
                              ↓
                          PRIORIZA
                              ↓
                           EXPLICA
```

Y cerraría esa sección con una frase que para mí resume **muy bien tu idea**:

> ### No importa en qué etapa esté tu proyecto.
>
> **Si hay algo para analizar, hay calidad para trabajar.**

Esa última frase incluso podría convertirse en una de las frases fuertes de marca de Breakers.

Y haría una corrección conceptual desde ahora en toda nuestra documentación: **Breakers no es una plataforma de “testing”. Es una plataforma de calidad y riesgo.** Testing es una de las capacidades que puede utilizar para encontrar evidencia, no la frontera del producto.
