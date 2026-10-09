"""Create and store demo support tickets."""
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime
from typing import Any

from react_agent.database import DB_PATH, find_shipment


def create_ticket(shipment_id: str) -> dict[str, Any]:
    """Create one ticket per shipment, returning an existing one on retry."""
    shipment_id = shipment_id.strip().upper()
    shipment = find_shipment(shipment_id)
    if shipment is None:
        return {'error': 'Shipment not found. No ticket created.'}
    if shipment['status'] == 'delivered':
        return {'error': 'Shipment is delivered. No exception ticket needed.'}
    ticket_id = f'TKT-{uuid.uuid4().hex[:10].upper()}'
    reason = shipment['events'][-1]['event']
    created_at = datetime.now(UTC).isoformat()
    with closing(sqlite3.connect(DB_PATH, timeout=10)) as connection:
        connection.row_factory = sqlite3.Row
        with connection:
            connection.execute('\n                CREATE TABLE IF NOT EXISTS tickets (\n                    ticket_id TEXT PRIMARY KEY,\n                    shipment_id TEXT NOT NULL UNIQUE,\n                    reason TEXT NOT NULL,\n                    status TEXT NOT NULL,\n                    created_at TEXT NOT NULL\n                )\n            ')
            cursor = connection.execute('\n                INSERT OR IGNORE INTO tickets\n                (ticket_id, shipment_id, reason, status, created_at)\n                VALUES (?, ?, ?, ?, ?)\n                ', (ticket_id, shipment_id, reason, 'open', created_at))
            created = cursor.rowcount == 1
            row = connection.execute('SELECT * FROM tickets WHERE shipment_id = ?', (shipment_id,)).fetchone()
    return {'created': created, **dict(row)}
