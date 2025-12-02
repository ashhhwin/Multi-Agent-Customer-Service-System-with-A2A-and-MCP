from fastapi import FastAPI, Request
from agents.agent_client import AgentConnector, create_a2a_message, check_message_schema, generate_error_response
from agents.llm_service import query_llm
import uvicorn
import logging
import asyncio
import json

app = FastAPI(title="Support Agent")
agent = AgentConnector()

logging.basicConfig(
    filename="logs/support_agent.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

@app.get("/agent_card")
def get_card():
    return {
        "name": "Support Agent",
        "description": "Handles tickets and support logic with LLM generation.",
        "tools": ["create_ticket", "list_tickets"],
        "a2a_protocol": "REST_HTTP_JSON"
    }

# -------------------------
# LLM Response Generation
# -------------------------
def generate_polite_response(action_taken, details, customer_text):
    """
    Asks LLM to phrase the system action as a short chat message.
    """
    system_prompt = f"""
    You are a helpful Customer Support Chatbot.
    
    User Query: "{customer_text}"
    System Action: {action_taken}
    Details: {json.dumps(details, default=str)}
    
    INSTRUCTIONS:
    - Draft a very short, direct chat response (1-2 sentences).
    - CONFIRM the action was done.
    - NO "Dear Customer" headers.
    - NO "Best Regards" signatures.
    - NO emails. Be conversational and concise.
    """
    
    # We want text output, not JSON
    response = query_llm(system_prompt, "Draft chat response", json_mode=False)
    
    if not response:
        return f"Action processed: {action_taken}"
    return response

# -------------------------
# Intent handlers
# -------------------------
async def handle_support_intent(intent: str, payload: dict):
    customer_id = payload.get("customer_id")
    text = payload.get("text", "")
    entities = payload.get("entities", {}) 
    
    # Logic Processing
    response_data = {}
    action_description = ""

    if intent == "support_request":
        action_description = "General inquiry logged."
        response_data = {"status": "ok"}

    elif intent == "refund_request":
        action_description = "Refund initiated successfully."
        response_data = {"status": "ok", "refund_id": "REF-998877"}

    elif intent == "cancel_subscription":
        action_description = "Subscription cancelled."
        response_data = {"status": "ok"}

    elif intent == "upgrade_request":
        action_description = "Upgrade processed."
        response_data = {"status": "ok"}

    elif intent == "show_ticket_status":
        if not customer_id:
            return {"status": "error", "error": "Missing customer_id"}
        
        tickets = await agent.invoke_tool("list_tickets", {"customer_ids": [customer_id]})
        
        if isinstance(tickets, list) and len(tickets) > 0:
            count = len(tickets)
            action_description = f"Found {count} tickets."
        else:
            action_description = "No tickets found."
            
        response_data = tickets

    elif intent == "escalate_issue":
        reason = entities.get("reason") or text
        ticket = await agent.invoke_tool("create_ticket", {
            "customer_id": customer_id,
            "issue": reason,
            "priority": "medium"
        })
        ticket_id = ticket.get('id', 'unknown')
        action_description = f"Escalation Ticket #{ticket_id} created."
        response_data = ticket

    else:
        return {"status": "error", "error": f"Unknown intent: {intent}"}

    # Add the LLM voice to the response
    if action_description:
        llm_message = generate_polite_response(action_description, response_data, text)
        
        if isinstance(response_data, list):
            return {
                "data": response_data,
                "answer_text": llm_message
            }
        
        if isinstance(response_data, dict):
            response_data["answer_text"] = llm_message
            return response_data

    return response_data

@app.post("/a2a")
async def a2a_handler(request: Request):
    msg = await request.json()
    try:
        check_message_schema(msg)
        intents = msg["intent"]
        payload = msg["payload"]
        
        if not isinstance(intents, list): intents = [intents]
        
        tasks = [handle_support_intent(intent, payload) for intent in intents]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        return create_a2a_message("support_agent", msg["from"], intents, results, "response", msg["correlation_id"])

    except Exception as e:
        return generate_error_response(msg, str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8102)