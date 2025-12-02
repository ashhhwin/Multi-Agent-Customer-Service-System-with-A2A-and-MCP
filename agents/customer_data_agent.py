import asyncio
import logging
import uvicorn

from fastapi import FastAPI, Request
from agents.agent_client import AgentConnector, create_a2a_message, check_message_schema, generate_error_response

app = FastAPI(title="Customer Data Agent")
agent = AgentConnector()

logging.basicConfig(
    filename="logs/customer_data_agent.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

@app.get("/agent_card")
def get_card():
    return {
        "name": "Customer Data Agent",
        "description": "Accesses database via MCP to fetch/update customer info.",
        "input_schema": {"intent": "string", "payload": "object"},
        "tools": ["get_customer", "update_customer", "list_customers"],
        "a2a_protocol": "REST_HTTP_JSON"
    }

def normalize_payload(payload: dict):
    """Ensure customer_id key exists for MCP tool calls."""
    return {"customer_id": payload["customer_id"]} if "customer_id" in payload else payload

# -------------------------
# Intent handler (WITH ALIASES)
# -------------------------
async def handle_customer_intent(intent: str, payload: dict):
    """Async handler for each customer data intent."""
    
    # --- GET CUSTOMER INFO ALIASES (Fixes Scenario 1) ---
    if intent in ["get_customer_info", "get_customer_info_by_id"]:
        return await agent.invoke_tool("get_customer", normalize_payload(payload))

    elif intent == "list_customers":
        return await agent.invoke_tool("list_customers", payload)

    elif intent == "update_email":
        updates = payload.get("updates", {})
        return await agent.invoke_tool("update_customer", {"customer_id": payload["customer_id"], "data": updates})

    elif intent == "update_customer":
        return await agent.invoke_tool("update_customer", payload)

    elif intent == "get_customer_history":
        return await agent.invoke_tool("get_customer_history", normalize_payload(payload))

    else:
        return {"status": "error", "data": f"Unknown intent: {intent}"}

# -------------------------
# A2A endpoint
# -------------------------
@app.post("/a2a")
async def handle_a2a(request: Request):
    msg = await request.json()
    try:
        check_message_schema(msg)
        intents = msg["intent"]
        payload = msg["payload"]
        cid = msg["correlation_id"]

        if not isinstance(intents, list):
            intents = [intents]

        tasks = [handle_customer_intent(intent, payload) for intent in intents]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        return create_a2a_message(
            sender_id="customer_data_agent",
            recipient_id=msg["from"],
            intent=intents,
            msg_type="response",
            content=results,
            corr_id=cid
        )

    except Exception as e:
        return generate_error_response(msg, str(e))

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8101)