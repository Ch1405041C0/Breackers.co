from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class KnowledgeHeuristic:
    id: str
    domain: str
    trigger_terms: tuple[str, ...]
    question: str
    rationale: str
    knowledge_ref: str
    reference_url: str
    kind: str = "DEFINITION_GAP"


@dataclass(frozen=True)
class KnowledgeFinding:
    id: str
    domain: str
    question: str
    rationale: str
    knowledge_ref: str
    reference_url: str
    kind: str


HEURISTICS = (
    KnowledgeHeuristic("KB-AUTH-001","AUTHENTICATION",("login","iniciar sesion","autentic"),"¿Está definido cómo se recupera o restablece el acceso cuando el usuario no puede autenticarse?","El flujo de autenticación menciona acceso pero no necesariamente define recuperación de credenciales.","OWASP-WSTG-ATHN","https://wstg.owasp.org/latest/4-Web_Application_Security_Testing/04-Authentication/","RISK_SUGGESTION"),
    KnowledgeHeuristic("KB-AUTH-002","AUTHENTICATION",("login","iniciar sesion","autentic"),"¿Está definido si existen canales alternativos o MFA y cómo afectan al inicio de sesión?","Los mecanismos alternativos pueden cambiar el comportamiento y la cobertura requerida.","OWASP-WSTG-ATHN-11","https://wstg.owasp.org/latest/4-Web_Application_Security_Testing/04-Authentication/11-Multi-Factor_Authentication/","RISK_SUGGESTION"),
    KnowledgeHeuristic("KB-LOCK-001","AUTHENTICATION",("bloquead","intentos","fallid"),"¿Cómo y cuándo se desbloquea una cuenta bloqueada?","Definir el bloqueo sin su recuperación deja incompleto el ciclo de estado de la cuenta.","OWASP-WSTG-ATHN","https://wstg.owasp.org/v4.1/4-Web_Application_Security_Testing/04-Authentication_Testing/README/"),
    KnowledgeHeuristic("KB-SESS-001","SESSION",("sesion","inactividad","timeout"),"¿La expiración invalida también la sesión del lado servidor y qué ocurre con una petición posterior?","El cierre visual no basta para definir una terminación segura de sesión.","OWASP-WSTG-SESS-06","https://wstg.owasp.org/latest/4-Web_Application_Security_Testing/06-Session_Management/06-Logout_Functionality/"),
    KnowledgeHeuristic("KB-SESS-002","SESSION",("sesion","login","iniciar sesion"),"¿Está definido el comportamiento ante múltiples sesiones simultáneas del mismo usuario?","Las sesiones concurrentes pueden estar permitidas o restringidas; el comportamiento debe ser una decisión del producto.","OWASP-WSTG-SESS-11","https://wstg.owasp.org/latest/4-Web_Application_Security_Testing/06-Session_Management/11-Concurrent_Sessions/","RISK_SUGGESTION"),
    KnowledgeHeuristic("KB-INP-001","INPUT_VALIDATION",("usuario","contrasena","campo"),"¿Están definidos longitud mínima/máxima, caracteres permitidos y tratamiento de espacios para los campos de entrada?","Sin límites y reglas de entrada no se pueden derivar particiones y fronteras completas.","ISO-IEC-IEEE-29119-4:2021","https://www.iso.org/standard/79430.html"),
    KnowledgeHeuristic("KB-INP-002","INPUT_VALIDATION",("usuario","contrasena","campo"),"¿Está definida la sensibilidad a mayúsculas/minúsculas para cada campo relevante?","La equivalencia de entradas cambia según la normalización definida por el producto.","ISO-IEC-IEEE-29119-4:2021","https://www.iso.org/standard/79430.html"),
    KnowledgeHeuristic("KB-AUTH-003","AUTHENTICATION",("contrasena","credencial","login"),"¿Está definido que las credenciales se transportan únicamente por un canal cifrado?","La especificación funcional puede omitir una condición de seguridad necesaria para evaluar el flujo de autenticación.","OWASP-WSTG-ATHN-01","https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/04-Authentication_Testing/01-Testing_for_Credentials_Transported_over_an_Encrypted_Channel/","RISK_SUGGESTION"),
)


def analyze_knowledge_gaps(texts: tuple[str, ...]) -> tuple[KnowledgeFinding, ...]:
    corpus = _norm("\n".join(texts))
    findings = []
    for heuristic in HEURISTICS:
        if not any(_norm(term) in corpus for term in heuristic.trigger_terms):
            continue
        if _already_defined(heuristic, corpus):
            continue
        findings.append(KnowledgeFinding(
            f"KF-{len(findings)+1:03d}", heuristic.domain, heuristic.question,
            heuristic.rationale, heuristic.knowledge_ref, heuristic.reference_url, heuristic.kind
        ))
    return tuple(findings)


def _already_defined(h: KnowledgeHeuristic, corpus: str) -> bool:
    checks = {
        "KB-LOCK-001": ("desbloque", "desbloqueo"),
        "KB-SESS-001": ("invalida", "servidor"),
        "KB-SESS-002": ("sesiones simultaneas", "sesiones concurrentes"),
        "KB-INP-001": ("longitud maxima", "longitud minima", "caracteres permitidos"),
        "KB-INP-002": ("sensible a mayusculas", "distingue mayusculas"),
        "KB-AUTH-003": ("https", "canal cifrado", "tls"),
        "KB-AUTH-001": ("recuperar contrasena", "restablecer contrasena"),
        "KB-AUTH-002": ("mfa", "doble factor", "segundo factor"),
    }
    terms = checks.get(h.id, ())
    return any(_norm(term) in corpus for term in terms)


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", value)
