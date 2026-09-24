import re
from pathlib import Path

from ..risk.engine import make_risk

RULES = [
    {
        "name": "undefined_error_flow",
        "area": "error_handling",
        "severity": "HIGH",
        "needles": ("error", "rechazo", "rechazada", "fallo", "timeout", "expira"),
        "title": "Flujo de error o excepción potencialmente incompleto",
        "hypothesis": "El requisito menciona una condición de error/excepción pero puede no definir completamente recuperación, mensaje o estado final.",
        "missing": ["resultado esperado", "mensaje al usuario", "estado final o recuperación"],
    },
    {
        "name": "boundary_without_behavior",
        "area": "business_rules",
        "severity": "MEDIUM",
        "needles": ("máximo", "maximo", "mínimo", "minimo", "límite", "limite", "hasta "),
        "title": "Regla de límite requiere comportamiento de borde",
        "hypothesis": "Existe un límite de negocio y conviene verificar qué ocurre debajo, exactamente en el límite y por encima.",
        "missing": ["comportamiento en el límite", "comportamiento fuera del límite"],
    },
    {
        "name": "conditional_rule",
        "area": "business_rules",
        "severity": "MEDIUM",
        "needles": ("si ", "cuando ", "en caso de"),
        "title": "Regla condicional requiere camino alternativo",
        "hypothesis": "Se define una condición y puede faltar el comportamiento cuando esa condición no se cumple.",
        "missing": ["camino alternativo", "estado esperado cuando la condición es falsa"],
    },
]


def _sentences(text: str):
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+|\n+", text) if x.strip()]


def analyze_requirements_text(text: str, reference: str = "functional_document"):
    risks = []
    for index, sentence in enumerate(_sentences(text), start=1):
        lowered = sentence.lower()
        for rule in RULES:
            if any(needle in lowered for needle in rule["needles"]):
                risks.append(make_risk(
                    area=rule["area"], severity=rule["severity"], title=rule["title"],
                    hypothesis=rule["hypothesis"], source_type="functional_document",
                    reference=f"{reference}#fragment-{index}", excerpt=sentence[:500],
                    confidence=0.55, missing_evidence=rule["missing"],
                    suggested_action="Aclarar la regla antes de convertirla en desarrollo y pruebas.",
                ))
    return risks


def analyze_requirements_file(target: str):
    path = Path(target)
    if path.suffix.lower() not in {".txt", ".md"}:
        return [], ["El adaptador v0.1 analiza texto/Markdown. PDF y DOCX quedan declarados como fuentes pendientes de extracción."]
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return [], ["No se pudo extraer texto legible del documento."]
    return analyze_requirements_text(text, path.name), []
