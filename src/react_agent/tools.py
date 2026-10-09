"""Tools for looking up synthetic shipments stored in SQLite."""
from typing import Any

from langchain_core.tools import tool

from react_agent.database import find_shipment, initialize_database

SHIPMENTS = {'SHP1001': {'shipment_id': 'SHP1001', 'carrier': 'DemoExpress', 'status': 'delivered', 'events': [{'time': '2026-10-07 09:00 IST', 'event': 'Picked up'}, {'time': '2026-10-08 08:00 IST', 'event': 'Out for delivery'}, {'time': '2026-10-08 14:30 IST', 'event': 'Delivered'}], 'recommended_action': 'No delivery action required.'}, 'SHP1002': {'shipment_id': 'SHP1002', 'carrier': 'DemoExpress', 'status': 'delivery_exception', 'events': [{'time': '2026-10-07 10:00 IST', 'event': 'Picked up'}, {'time': '2026-10-08 09:00 IST', 'event': 'Out for delivery'}, {'time': '2026-10-08 16:00 IST', 'event': 'Delivery failed: incomplete address'}], 'recommended_action': 'Contact the customer to confirm the complete address, then request a delivery reattempt from the carrier.'}}
initialize_database(SHIPMENTS)

@tool
def get_shipment(shipment_id: str) -> dict[str, Any]:
    """Look up a synthetic shipment by ID and return its tracking events."""
    shipment_id = shipment_id.strip().upper()
    shipment = find_shipment(shipment_id)
    if shipment is None:
        return {'found': False, 'shipment_id': shipment_id, 'message': 'No matching shipment exists in the demo dataset.'}
    return {'found': True, 'data_source': 'synthetic demo records stored in SQLite', **shipment}
