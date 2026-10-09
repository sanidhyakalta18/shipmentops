"""Persistent storage for synthetic shipment records."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, cast

DB_PATH = Path(__file__).resolve().parents[2] / 'shipmentops.db'

def initialize_database(shipments: dict[str, Any]) -> None:
    """Create the table and insert missing demo records."""
    with closing(sqlite3.connect(DB_PATH)) as connection:
        with connection:
            connection.execute('\n                CREATE TABLE IF NOT EXISTS shipments (\n                    shipment_id TEXT PRIMARY KEY,\n                    record_json TEXT NOT NULL\n                )\n            ')
            connection.executemany('\n                INSERT OR IGNORE INTO shipments\n                (shipment_id, record_json)\n                VALUES (?, ?)\n                ', [(shipment_id, json.dumps(record)) for shipment_id, record in shipments.items()])

def find_shipment(shipment_id: str) -> dict[str, Any] | None:
    """Retrieve a shipment using a parameterized SQL query."""
    with closing(sqlite3.connect(DB_PATH)) as connection:
        row = connection.execute('SELECT record_json FROM shipments WHERE shipment_id = ?', (shipment_id,)).fetchone()
    return cast(dict[str, Any], json.loads(row[0])) if row else None
