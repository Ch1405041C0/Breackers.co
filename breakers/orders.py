from __future__ import annotations

from datetime import datetime, timezone
import uuid

from .storage import SQLiteStore

PRODUCT_CATALOG = {"scan": {"currency": "ARS", "amount": 99900}}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

class OrderStore:
    def __init__(self, database: SQLiteStore):
        self.database = database

    def create(self, product: str, resource_id: str) -> dict:
        if product not in {"scan", "strike", "control"}:
            raise ValueError("Producto inválido.")
        price = PRODUCT_CATALOG.get(product)
        if price is None:
            raise ValueError("Este producto todavía no está disponible para compra.")
        order_id, now = uuid.uuid4().hex, _now()
        with self.database.connect() as connection:
            connection.execute("INSERT INTO orders(order_id, product, resource_id, currency, amount, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)", (order_id, product, resource_id, price["currency"], price["amount"], now, now))
        return self.get(order_id)

    def get(self, order_id: str) -> dict | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        return dict(row) if row else None

    def find_for_resource(self, product: str, resource_id: str) -> dict | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM orders WHERE product = ? AND resource_id = ? ORDER BY created_at DESC LIMIT 1", (product, resource_id)).fetchone()
        return dict(row) if row else None

    def has_approved_access(self, product: str, resource_id: str) -> bool:
        with self.database.connect() as connection:
            row = connection.execute("SELECT 1 FROM orders WHERE product = ? AND resource_id = ? AND status = 'approved' LIMIT 1", (product, resource_id)).fetchone()
        return row is not None
