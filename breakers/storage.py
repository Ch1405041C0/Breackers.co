from __future__ import annotations

from pathlib import Path
import sqlite3


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS interventions (
    intervention_id TEXT PRIMARY KEY,
    public_breakers_id TEXT NOT NULL UNIQUE,
    product TEXT NOT NULL CHECK(product IN ('scan', 'strike', 'control')),
    resource_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_interventions_public_id ON interventions(public_breakers_id);
CREATE INDEX IF NOT EXISTS idx_interventions_resource ON interventions(product, resource_id);

CREATE TABLE IF NOT EXISTS scans (
    scan_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL UNIQUE,
    public_summary TEXT NOT NULL,
    full_report TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(scan_id) REFERENCES scans(scan_id)
);

CREATE TABLE IF NOT EXISTS scan_antecedents (
    intervention_id TEXT PRIMARY KEY,
    snapshot TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(intervention_id) REFERENCES interventions(intervention_id)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    product TEXT NOT NULL CHECK(product IN ('scan', 'strike', 'control')),
    resource_id TEXT NOT NULL,
    currency TEXT NOT NULL,
    amount INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'approved', 'rejected', 'cancelled')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    approved_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_orders_resource ON orders(product, resource_id);
"""


class SQLiteStore:
    def __init__(self, path: str):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
