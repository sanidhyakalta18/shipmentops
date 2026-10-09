"""ShipmentOps chat and confirmed demo ticket creation."""

import logging
import uuid

from fasthtml.common import (
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

# Importing tools initializes the synthetic shipment database.
from react_agent import tools  # noqa: F401
from react_agent.database import find_shipment
from react_agent.tickets import create_ticket

client = get_client()

styles = Style("""
body {
    margin: 0;
    background: #f4f6f8;
    color: #17202a;
    font-family: Arial, sans-serif;
}
.container {
    max-width: 850px;
    margin: 24px auto;
    padding: 20px;
}
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
}
.chat, .ticket-panel {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 18px;
}
.chat { min-height: 220px; }
.message {
    padding: 14px;
    margin-bottom: 12px;
    border-radius: 10px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    line-height: 1.5;
}
.user { background: #e8efff; }
.assistant { background: #e8f6ee; }
.composer {
    display: flex;
    gap: 10px;
    margin-top: 14px;
}
input {
    flex: 1;
    min-width: 0;
    padding: 12px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    font-size: 16px;
}
button, .new-chat {
    background: #166534;
    color: white;
    padding: 12px 16px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    text-decoration: none;
}
button:disabled { opacity: 0.5; }
.subtitle { color: #64748b; }
.status { display: none; }
.status.htmx-request { display: block; }
#ticket-result { margin-top: 14px; }
""")

app = FastHTML(hdrs=(styles,))


def message_bubble(content: str, is_user: bool = False):
    """Render a chat message as safely escaped text."""
    label = "You" if is_user else "ShipmentOps"
    kind = "user" if is_user else "assistant"
    return Div(
        Div(label, style="font-weight:bold;margin-bottom:6px;"),
        Div(content),
        cls=f"message {kind}",
    )


def content_to_text(content):
    """Extract text from a model response."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            block if isinstance(block, str) else block.get("text", "")
            for block in content
            if isinstance(block, (str, dict))
        )
    return ""


@app.get("/")
async def home():
    """Redirect to a new conversation."""
    return RedirectResponse(
        f"/conversations/{uuid.uuid4()}",
        status_code=302,
    )


@app.get("/conversations/{thread_id}")
async def conversation(thread_id: str):
    """Display the conversation and ticket interface."""
    await client.threads.create(
        thread_id=thread_id,
        if_exists="do_nothing",
    )

    state = await client.threads.get_state(thread_id)
    messages = (state.get("values") or {}).get("messages", [])

    bubbles = []
    for message in messages:
        kind = message.get("type") or message.get("role")
        if kind in ("human", "user", "ai", "assistant"):
            text = content_to_text(message.get("content", ""))
            if text:
                bubbles.append(
                    message_bubble(
                        text,
                        is_user=kind in ("human", "user"),
                    )
                )

    return (
        Title("ShipmentOps"),
        Div(
            Div(
                H1("ShipmentOps"),
                A("New chat", href="/", cls="new-chat"),
                cls="header",
            ),
            P(
                "Local prototype · Synthetic shipment data",
                cls="subtitle",
            ),
            Div(*bubbles, id="chatlist", cls="chat", aria_live="polite"),
            Form(
                Input(
                    name="msg",
                    placeholder="Ask about SHP1001 or SHP1002...",
                    required=True,
                    autocomplete="off",
                ),
                Button("Send", type="submit"),
                hx_post=f"/conversations/{thread_id}/send-message",
                hx_target="#chatlist",
                hx_swap="beforeend",
                hx_indicator="#status",
                hx_disabled_elt="find button",
                hx_on__after_request=(
                    "if(event.detail.successful) this.reset()"
                ),
                cls="composer",
            ),
            P("ShipmentOps is thinking...", id="status", cls="status"),
            Div(
                H2("Demo support ticket"),
                P(
                    "Review a shipment before confirming a local ticket. "
                    "This does not contact a carrier or customer."
                ),
                Form(
                    Input(
                        name="shipment_id",
                        placeholder="Shipment ID, e.g. SHP1002",
                        required=True,
                    ),
                    Button("Review ticket", type="submit"),
                    hx_post="/tickets/preview",
                    hx_target="#ticket-result",
                    hx_swap="innerHTML",
                    cls="composer",
                ),
                Div(id="ticket-result", aria_live="polite"),
                cls="ticket-panel",
                style="margin-top:24px;",
            ),
            cls="container",
        ),
    )


@app.post("/conversations/{thread_id}/send-message")
async def send_message(thread_id: str, msg: str):
    """Send a message to the shipment agent."""
    msg = msg.strip()
    if not msg:
        return ""

    try:
        result = await client.runs.wait(
            thread_id=thread_id,
            assistant_id="agent",
            input={"messages": [{"role": "user", "content": msg}]},
        )

        if result.get("__error__"):
            raise RuntimeError("Agent run failed")

        answer = ""
        for message in reversed(result.get("messages", [])):
            kind = message.get("type") or message.get("role")
            if kind in ("ai", "assistant"):
                answer = content_to_text(message.get("content", ""))
                if answer:
                    break

        return (
            message_bubble(msg, is_user=True),
            message_bubble(answer or "The model returned no text."),
        )

    except Exception:
        logging.getLogger(__name__).exception("Chat request failed")
        return (
            message_bubble(msg, is_user=True),
            message_bubble(
                "Could not get a response. Check the server Terminal."
            ),
        )




@app.post("/tickets/preview")
async def preview_ticket(shipment_id: str):
    """Show ticket details before confirmation."""
    from starlette.concurrency import run_in_threadpool

    shipment_id = shipment_id.strip().upper()
    shipment = await run_in_threadpool(find_shipment, shipment_id)

    if shipment is None:
        return P("Shipment not found. No ticket created.")

    if shipment["status"] == "delivered":
        return P("Shipment is delivered. No exception ticket needed.")

    return Div(
        P(f"Shipment: {shipment_id}"),
        P(f"Reason: {shipment['events'][-1]['event']}"),
        P(f"Recommended action: {shipment['recommended_action']}"),
        P("Confirm to save a demo ticket in your local database."),
        Form(
            Input(
                type="hidden",
                name="shipment_id",
                value=shipment_id,
            ),
            Button("Confirm ticket creation", type="submit"),
            hx_post="/tickets/create",
            hx_target="#ticket-result",
            hx_swap="innerHTML",
            hx_disabled_elt="find button",
        ),
    )


@app.post("/tickets/create")
async def confirm_ticket(shipment_id: str):
    """Save a confirmed demo ticket."""
    from starlette.concurrency import run_in_threadpool

    ticket = await run_in_threadpool(create_ticket, shipment_id)

    if "error" in ticket:
        return P(ticket["error"])

    label = (
        "Ticket created"
        if ticket["created"]
        else "Ticket already exists"
    )

    return Div(
        P(f"{label}: {ticket['ticket_id']}"),
        P(f"Shipment: {ticket['shipment_id']}"),
        P(f"Status: {ticket['status']}"),
        P(f"Reason: {ticket['reason']}"),
        P("Saved locally. No carrier or customer was contacted."),
    )