"""Persistent storage for synthetic shipment records."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "shipmentops.db"


def initialize_database(shipments: dict):
    """Create the table and insert missing demo records."""
    with closing(sqlite3.connect(DB_PATH)) as connection:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS shipments (
                    shipment_id TEXT PRIMARY KEY,
                    record_json TEXT NOT NULL
                )
            """)

            connection.executemany(
                """
                INSERT OR IGNORE INTO shipments
                (shipment_id, record_json)
                VALUES (?, ?)
                """,
                [
                    (shipment_id, json.dumps(record))
                    for shipment_id, record in shipments.items()
                ],
            )


def find_shipment(shipment_id: str):
    """Retrieve a shipment using a parameterized SQL query."""
    with closing(sqlite3.connect(DB_PATH)) as connection:
        row = connection.execute(
            "SELECT record_json FROM shipments WHERE shipment_id = ?",
            (shipment_id,),
        ).fetchone()

    return json.loads(row[0]) if row else None