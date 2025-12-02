import asyncio
import logging
import uvicorn
import os
import json

from fastapi import FastAPI, Request
from agents.agent_client import AgentConnector, create_a2a_message, check_message_schema, generate_error_response
from agents.llm_service import query_llm

# -------------------------
# Configuration
# -------------------------
if "HF_TOKEN" not in os.environ:
    os.environ['HF_TOKEN'] = "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"

SUPPORT_AGENT_URL = "http://127.0.0.1:8102"
DATA_AGENT_URL = "http://127.0.0.1:8101"

# -------------------------
# App & Logger Setup
# -------------------------
app = FastAPI(title="Router Agent")
agent = AgentConnector()

logger = logging.getLogger("RouterAgent")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(handler)

@app.get("/agent_card")
def get_card():
    return {
        "name": "Router Agent",
        "description": "Orchestrator. Uses LLM to analyze intent and route tasks to specialists.",
        "input_schema": {"text": "string", "customer_id": "int"},
        "output_schema": {"results": "array"},
        "a2a_protocol": "REST_HTTP_JSON"
    }

# -------------------------
# 1. The "Brain" (LLM Classification)
# -------------------------
def classify_intents_with_llm(text: str):
    """
    Uses LLM to analyze the user query for intent detection (Primary method).
    """
    logger.info(f"\n[ROUTER] Analyzing Input: '{text}'")

    system_prompt = """
    You are the Senior Orchestrator for a Customer Service System. 
    Your job is to analyze the user's request and route it to the correct internal function.
    
    [List of AVAILABLE INTENTS provided here for LLM]

    INSTRUCTIONS:
    1. specific_reasoning: Explain WHY you chose the intent in 1 short sentence.
    2. intents: The list of matching intents (usually 1, but can be multiple).
    3. entities: Extract 'email', 'status_filter', or 'reason'.

    """
    
    # Primary LLM Call
    response = query_llm(system_prompt, text, json_mode=True)
    
    if response and isinstance(response, dict):
        intents = response.get("intents", [])
        entities = response.get("entities", {})
        reasoning = response.get("reasoning", "No reasoning provided")
        
        logger.info(f"[ROUTER] LLM Thought: {reasoning}")
        logger.info(f"[ROUTER] Detected Intent: {intents}")
        return intents, entities
    
    # --- FALLBACK LOGIC (Robust Multi-Intent Detection) ---
    logger.warning("[ROUTER] LLM Failed or Timed Out. Using Robust Regex Fallback.")
    intents = []
    text_lower = text.lower()
    
    # We use independent IF statements so multiple intents can trigger at once
    if "refund" in text_lower or "money back" in text_lower: 
        intents.append("refund_request")
        
    if "cancel" in text_lower: 
        intents.append("cancel_subscription")
        
    if "upgrade" in text_lower:
        intents.append("upgrade_request")
        
    if "active" in text_lower and "customers" in text_lower: 
        intents.append("list_customers")
        
    if "email" in text_lower and "update" in text_lower: 
        intents.append("update_email")
        
    if "history" in text_lower or "past tickets" in text_lower: 
        intents.append("get_customer_history")
        
    if "ticket" in text_lower or "status" in text_lower: 
        intents.append("show_ticket_status")
        
    # CRITICAL CHECK for Scenario 6: Catches "billing issues" or "complaint"
    if "billing" in text_lower or "issues" in text_lower or "complaining" in text_lower:
        # If cancellation/refund was caught, this adds the necessary second intent for escalation
        if "escalate_issue" not in intents:
            intents.append("escalate_issue")
            
    # Default if nothing matched
    if not intents:
        intents.append("support_request")
    
    logger.info(f"[ROUTER] Fallback Intent: {intents}")
    return intents, {}

# -------------------------
# 2. Task Routing Logic
# -------------------------
def build_agent_task(intent: str, customer_id: int, text: str, entities: dict):
    requires_escalation = False
    recipient_name = "Unknown"

    # --- ROUTE TO DATA SPECIALIST ---
    if intent in ["get_customer_info", "get_customer_history", "update_email", "list_customers"]:
        recipient = "customer_data_agent"
        target_url = DATA_AGENT_URL
        payload = {"customer_id": customer_id}
        recipient_name = "Data Agent"
        
        if intent == "list_customers":
            status = entities.get("status_filter")
            if not status and "active" in text.lower(): status = "active"
            if status: status = status.lower()
            payload["status"] = status

        if intent == "update_email":
            new_email = entities.get("email")
            if not new_email:
                import re
                match = re.search(r'[\w\.-]+@[\w\.-]+', text)
                if match: new_email = match.group(0)
            
            payload["updates"] = {"email": new_email} if new_email else {}
            requires_escalation = True

    # --- ROUTE TO SUPPORT SPECIALIST ---
    else:
        recipient = "support_agent"
        target_url = SUPPORT_AGENT_URL
        recipient_name = "Support Agent"
        
        payload = {
            "customer_id": customer_id, 
            "text": text,
            "entities": entities
        }

        if intent in ["refund_request", "cancel_subscription", "upgrade_request", "escalate_issue"]:
            requires_escalation = True

    logger.info(f"[ROUTER] Handoff: Sending '{intent}' to {recipient_name}")

    msg = create_a2a_message(
        sender_id="router",
        recipient_id=recipient,
        intent=intent,
        content=payload
    )

    return target_url, msg, intent, requires_escalation

# -------------------------
# 3. Main Query Endpoint
# -------------------------
@app.post("/query")
async def query_endpoint(request: Request):
    body = await request.json()
    text = body.get("text")
    customer_id = body.get("customer_id")

    if not text or not customer_id:
        return {"status": "error", "message": "Missing 'text' or 'customer_id'"}

    intents, entities = classify_intents_with_llm(text)

    tasks = []
    task_metadata = []
    for intent in intents:
        target_url, msg, intent_name, requires_escalation = build_agent_task(intent, customer_id, text, entities)
        tasks.append(asyncio.to_thread(agent.send_message, target_url, msg))
        task_metadata.append({"intent": intent_name, "requires_escalation": requires_escalation})

    logger.info(f"[ROUTER] Waiting for {len(tasks)} agent(s) to respond...")
    results_raw = await asyncio.gather(*tasks, return_exceptions=True)

    results = []
    for meta, res in zip(task_metadata, results_raw):
        status = "error"
        data = None
        
        if isinstance(res, Exception):
            logger.error(f"[ROUTER] Agent Execution Failed: {res}")
            data = str(res)
        elif isinstance(res, dict):
            if "payload" in res:
                payload_list = res.get("payload", [])
                if isinstance(payload_list, list) and len(payload_list) > 0:
                    data = payload_list[0] 
                    if isinstance(data, dict):
                        status = data.get("status", "ok")
                    else:
                        status = "ok"
                else:
                    status = "ok"
                    data = payload_list
            else:
                status = res.get("status", "unknown")
                data = res.get("data") or res.get("error")
        
        results.append({
            "intent": meta["intent"],
            "status": status,
            "data": data,
            "requires_escalation": meta["requires_escalation"]
        })

    logger.info(f"[ROUTER] Request Complete. Returning {len(results)} result(s).\n")
    return {"status": "ok", "results": results}

# -------------------------
# A2A Interface
# -------------------------
@app.post("/a2a")
async def a2a_handler(request: Request):
    """Standard Agent-to-Agent listener (Required for protocol compliance)"""
    msg = await request.json()
    return create_a2a_message("router", msg["from"], msg["intent"], {"status": "ok"}, "response", msg["correlation_id"])

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8100)
