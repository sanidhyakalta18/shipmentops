# ShipmentOps

An AI shipment-support prototype built with Python, Gemini, LangGraph,
FastHTML and SQLite.

ShipmentOps retrieves synthetic tracking records, explains delivery
exceptions and recommends a next action. Users can review and confirm
a demo support ticket, which is stored locally in SQLite.

## Features

- Tool-based shipment lookup through a LangGraph agent.
- Answers grounded in synthetic tracking events.
- Handling for unknown shipment IDs.
- Persistent SQLite shipment and ticket storage.
- Review-and-confirm interface for ticket creation.
- Duplicate prevention: repeated submissions return the existing ticket.
- Basic automated evaluations with saved answers, tool calls and latency.

## Demo scenarios

| Shipment | Scenario |
|---|---|
| SHP1001 | Delivered shipment |
| SHP1002 | Failed delivery caused by an incomplete address |
| SHP9999 | Unknown shipment |

Try:

- “What is the status of SHP1001?”
- “Why is SHP1002 delayed, and what should support do next?”
- “Where is SHP9999?”

To create a ticket, enter SHP1002 in the ticket section, select
**Review ticket**, then **Confirm ticket creation**.

Tickets are local demo records. No customer or carrier is contacted.

## Architecture

The FastHTML interface sends chat requests to the LangGraph server.
The Gemini-powered agent calls `get_shipment`, which retrieves a
record from SQLite.

Ticket creation uses separate web routes. SQLite operations in those
async routes run in worker threads. A unique shipment constraint
prevents duplicate tickets.

## Run locally

Requires Python 3.12 and uv.

```bash
git clone https://github.com/sanidhyakalta18/shipmentops.git
cd shipmentops
uv sync --dev --python 3.12
```

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_key_here
LANGSMITH_TRACING=false
```

Start the development server:

```bash
uv run langgraph dev --no-browser
```

Open http://127.0.0.1:2024.

The application creates `shipmentops.db` and seeds missing demo
shipments automatically.

## Evaluations

```bash
uv run python evaluate.py
```

Results are saved in `evaluation_report.json`.

The initial run passed 5/5 basic regression checks covering:

1. Delivered shipment status.
2. Delivery exception explanation.
3. Recommended next action.
4. Unknown shipment handling.
5. Lowercase shipment IDs.

These checks inspect tool calls and expected answer phrases.
They are not a comprehensive factual-accuracy benchmark.
Valid paraphrases may fail keyword checks, and incorrect answers
may still pass. Review the saved answers manually.

## Project files

- `src/react_agent/graph.py`: model and agent instructions.
- `src/react_agent/tools.py`: shipment lookup tool and seed records.
- `src/react_agent/database.py`: SQLite shipment storage.
- `src/react_agent/tickets.py`: persistent demo ticket creation.
- `src/react_agent/app.py`: chat interface and ticket routes.
- `evaluate.py`: evaluation runner.
- `evaluation_report.json`: recorded evaluation results.

## Current limitations

- Two synthetic shipment records; no live carrier integration.
- Local development prototype; public deployment is pending.
- No production authentication or access controls.
- Tickets represent one demo exception per shipment.
- Conversation persistence is managed by the development runtime.
- Prompt instructions reduce unsupported claims but do not guarantee
  that every answer is correct.

## Attribution

Adapted from LangChain's MIT-licensed full-stack Python starter:

https://github.com/langchain-ai/langgraph-fullstack-python

Project additions include Gemini integration, the shipment-support
workflow, SQLite storage, confirmed ticket creation, duplicate
prevention and basic evaluations. Development used AI assistance.

The original license and copyright notices are retained.
