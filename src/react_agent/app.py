"""ShipmentOps chat and confirmed demo ticket creation."""
import logging
import uuid
from typing import Any

from fasthtml.common import (  # type: ignore[import-untyped]
    H1,
    H2,
    A,
    Button,
    Div,
    FastHTML,
    Form,
    Input,
    P,
    Style,
    Title,
)
from langgraph_sdk import get_client
from starlette.responses import RedirectResponse

from react_agent import tools  # noqa: F401
from react_agent.database import find_shipment
from react_agent.tickets import create_ticket

client: Any = get_client()
styles = Style('\nbody {\n    margin: 0;\n    background: #f4f6f8;\n    color: #17202a;\n    font-family: Arial, sans-serif;\n}\n.container {\n    max-width: 850px;\n    margin: 24px auto;\n    padding: 20px;\n}\n.header {\n    display: flex;\n    justify-content: space-between;\n    align-items: center;\n    gap: 12px;\n}\n.chat, .ticket-panel {\n    background: white;\n    border: 1px solid #e2e8f0;\n    border-radius: 14px;\n    padding: 20px;\n    margin-bottom: 18px;\n}\n.chat { min-height: 220px; }\n.message {\n    padding: 14px;\n    margin-bottom: 12px;\n    border-radius: 10px;\n    white-space: pre-wrap;\n    overflow-wrap: anywhere;\n    line-height: 1.5;\n}\n.user { background: #e8efff; }\n.assistant { background: #e8f6ee; }\n.composer {\n    display: flex;\n    gap: 10px;\n    margin-top: 14px;\n}\ninput {\n    flex: 1;\n    min-width: 0;\n    padding: 12px;\n    border: 1px solid #cbd5e1;\n    border-radius: 8px;\n    font-size: 16px;\n}\nbutton, .new-chat {\n    background: #166534;\n    color: white;\n    padding: 12px 16px;\n    border: none;\n    border-radius: 8px;\n    cursor: pointer;\n    text-decoration: none;\n}\nbutton:disabled { opacity: 0.5; }\n.subtitle { color: #64748b; }\n.status { display: none; }\n.status.htmx-request { display: block; }\n#ticket-result { margin-top: 14px; }\n')
app = FastHTML(hdrs=(styles,))

def message_bubble(content: str, is_user: bool=False) -> Any:
    """Render a chat message as safely escaped text."""
    label = 'You' if is_user else 'ShipmentOps'
    kind = 'user' if is_user else 'assistant'
    return Div(Div(label, style='font-weight:bold;margin-bottom:6px;'), Div(content), cls=f'message {kind}')

def content_to_text(content: Any) -> str:
    """Extract text from a model response."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(block if isinstance(block, str) else block.get('text', '') for block in content if isinstance(block, (str, dict)))
    return ''

@app.get('/')  # type: ignore[untyped-decorator]
async def home() -> RedirectResponse:
    """Redirect to a new conversation."""
    return RedirectResponse(f'/conversations/{uuid.uuid4()}', status_code=302)

@app.get('/conversations/{thread_id}')  # type: ignore[untyped-decorator]
async def conversation(thread_id: str) -> Any:
    """Display the conversation and ticket interface."""
    await client.threads.create(thread_id=thread_id, if_exists='do_nothing')
    state = await client.threads.get_state(thread_id)
    messages = (state.get('values') or {}).get('messages', [])
    bubbles = []
    for message in messages:
        kind = message.get('type') or message.get('role')
        if kind in ('human', 'user', 'ai', 'assistant'):
            text = content_to_text(message.get('content', ''))
            if text:
                bubbles.append(message_bubble(text, is_user=kind in ('human', 'user')))
    return (Title('ShipmentOps'), Div(Div(H1('ShipmentOps'), A('New chat', href='/', cls='new-chat'), cls='header'), P('Local prototype · Synthetic shipment data', cls='subtitle'), Div(*bubbles, id='chatlist', cls='chat', aria_live='polite'), Form(Input(name='msg', placeholder='Ask about SHP1001 or SHP1002...', required=True, autocomplete='off'), Button('Send', type='submit'), hx_post=f'/conversations/{thread_id}/send-message', hx_target='#chatlist', hx_swap='beforeend', hx_indicator='#status', hx_disabled_elt='find button', hx_on__after_request='if(event.detail.successful) this.reset()', cls='composer'), P('ShipmentOps is thinking...', id='status', cls='status'), Div(H2('Demo support ticket'), P('Review a shipment before confirming a local ticket. This does not contact a carrier or customer.'), Form(Input(name='shipment_id', placeholder='Shipment ID, e.g. SHP1002', required=True), Button('Review ticket', type='submit'), hx_post='/tickets/preview', hx_target='#ticket-result', hx_swap='innerHTML', cls='composer'), Div(id='ticket-result', aria_live='polite'), cls='ticket-panel', style='margin-top:24px;'), cls='container'))

@app.post('/conversations/{thread_id}/send-message')  # type: ignore[untyped-decorator]
async def send_message(thread_id: str, msg: str) -> Any:
    """Send a message to the shipment agent."""
    msg = msg.strip()
    if not msg:
        return ''
    try:
        result = await client.runs.wait(thread_id=thread_id, assistant_id='agent', input={'messages': [{'role': 'user', 'content': msg}]})
        if result.get('__error__'):
            raise RuntimeError('Agent run failed')
        answer = ''
        for message in reversed(result.get('messages', [])):
            kind = message.get('type') or message.get('role')
            if kind in ('ai', 'assistant'):
                answer = content_to_text(message.get('content', ''))
                if answer:
                    break
        return (message_bubble(msg, is_user=True), message_bubble(answer or 'The model returned no text.'))
    except Exception:
        logging.getLogger(__name__).exception('Chat request failed')
        return (message_bubble(msg, is_user=True), message_bubble('Could not get a response. Check the server Terminal.'))

@app.post('/tickets/preview')  # type: ignore[untyped-decorator]
async def preview_ticket(shipment_id: str) -> Any:
    """Show ticket details before confirmation."""
    from starlette.concurrency import run_in_threadpool
    shipment_id = shipment_id.strip().upper()
    shipment = await run_in_threadpool(find_shipment, shipment_id)
    if shipment is None:
        return P('Shipment not found. No ticket created.')
    if shipment['status'] == 'delivered':
        return P('Shipment is delivered. No exception ticket needed.')
    return Div(P(f'Shipment: {shipment_id}'), P(f"Reason: {shipment['events'][-1]['event']}"), P(f"Recommended action: {shipment['recommended_action']}"), P('Confirm to save a demo ticket in your local database.'), Form(Input(type='hidden', name='shipment_id', value=shipment_id), Button('Confirm ticket creation', type='submit'), hx_post='/tickets/create', hx_target='#ticket-result', hx_swap='innerHTML', hx_disabled_elt='find button'))

@app.post('/tickets/create')  # type: ignore[untyped-decorator]
async def confirm_ticket(shipment_id: str) -> Any:
    """Save a confirmed demo ticket."""
    from starlette.concurrency import run_in_threadpool
    ticket = await run_in_threadpool(create_ticket, shipment_id)
    if 'error' in ticket:
        return P(ticket['error'])
    label = 'Ticket created' if ticket['created'] else 'Ticket already exists'
    return Div(P(f"{label}: {ticket['ticket_id']}"), P(f"Shipment: {ticket['shipment_id']}"), P(f"Status: {ticket['status']}"), P(f"Reason: {ticket['reason']}"), P('Saved locally. No carrier or customer was contacted.'))
