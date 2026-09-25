import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

SUPPORTED_HOSTS = {"github.com", "gitlab.com"}
REPOSITORY_URL_RE = re.compile(r"^https://(?:www\.)?(?:github\.com|gitlab\.com)/[^/\s]+/[^/\s]+/?$")


class RepositoryCloneError(ValueError):
    pass


def is_remote_repository(target: str) -> bool:
    try:
        parsed = urlparse(str(target).strip())
    except ValueError:
        return False
    return parsed.scheme == "https" and (parsed.hostname or "").lower() in SUPPORTED_HOSTS


def validate_repository_url(target: str) -> str:
    value = str(target or "").strip()
    if not is_remote_repository(value) or not REPOSITORY_URL_RE.match(value):
        raise ValueError("Repositorio remoto inválido. Use una URL HTTPS pública de GitHub o GitLab.")
    parsed = urlparse(value)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("La URL del repositorio no debe incluir credenciales, query string ni fragmentos.")
    return value[:-1] if value.endswith("/") else value


def clone_repository(url: str, destination: str | Path, timeout: int = 60) -> Path:
    url = validate_repository_url(url)
    destination = Path(destination)
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--no-tags", "--", url, str(destination)],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RepositoryCloneError(f"Timeout al clonar el repositorio después de {timeout}s.") from exc
    except OSError as exc:
        raise RepositoryCloneError("No se pudo ejecutar git para clonar el repositorio.") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        message = detail[-1] if detail else "error desconocido"
        raise RepositoryCloneError(f"No se pudo clonar el repositorio: {message}")
    if not destination.is_dir():
        raise RepositoryCloneError("Git finalizó sin crear el workspace esperado.")
    return destination


def repository_commit_sha(repository: str | Path, timeout: int = 10) -> str | None:
    repository = Path(repository)
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    sha = (result.stdout or "").strip()
    return sha if result.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40}", sha) else None
