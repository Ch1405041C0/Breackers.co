from __future__ import annotations

from dataclasses import dataclass
import secrets

PRODUCT_PREFIXES = {"scan": "SCN", "strike": "STR", "control": "CTL"}
PUBLIC_TOKEN_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
PUBLIC_TOKEN_LENGTH = 12


@dataclass(frozen=True)
class Intervention:
    intervention_id: str
    public_breakers_id: str
    product: str
    resource_id: str
    created_at: str


def generate_public_breakers_id(product: str) -> str:
    try:
        prefix = PRODUCT_PREFIXES[product.lower()]
    except (AttributeError, KeyError) as exc:
        raise ValueError("Producto de intervención inválido.") from exc
    token = "".join(secrets.choice(PUBLIC_TOKEN_ALPHABET) for _ in range(PUBLIC_TOKEN_LENGTH))
    return f"BRK-{prefix}-{token}"
