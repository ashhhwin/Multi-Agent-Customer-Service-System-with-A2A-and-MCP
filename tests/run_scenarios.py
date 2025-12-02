import requests
import json
import time
import sys

ROUTER_URL = "http://127.0.0.1:8100/query"

# ---------------------------------------------------------
# Test Scenarios
# ---------------------------------------------------------
scenarios = [
    {
        "name": "Scenario 1: Simple Query",
        "desc": "Single agent, straightforward MCP call",
        "payload": {"customer_id": 1, "text": "Get customer information for ID 1"}
    },
    {
        "name": "Scenario 2: Coordinated Query",
        "desc": "Multiple agents coordinate: data fetch + support response",
        "payload": {"customer_id": 12345, "text": "I'm customer 12345 and need help upgrading my account"}
    },
    {
        "name": "Scenario 3: Complex Query",
        "desc": "Requires negotiation between data and support agents",
        "payload": {"customer_id": 1, "text": "Show me all active customers who have open tickets"}
    },
    {
        "name": "Scenario 4: Escalation (Natural Language)",
        "desc": "Router identifies urgency via LLM and routes appropriately",
        "payload": {"customer_id": 1, "text": "I am really angry and want my money back right now!"}
    },
    {
        "name": "Scenario 5: Multi-Intent",
        "desc": "Parallel task execution (Update + History)",
        "payload": {"customer_id": 1, "text": "Update my email to new@email.com and show my ticket history"}
    },
    {
        "name": "Scenario 6: Negotiation/Billing",
        "desc": "Complex mixed intent handling",
        "payload": {"customer_id": 1, "text": "I want to cancel my subscription but I'm having billing issues"}
    }
]

# ---------------------------------------------------------
# Helper: Determine Handoff Target
# ---------------------------------------------------------
def get_handoff_target(intent):
    """
    Maps the intent to the specific agent responsible for it.
    This mimics the logic inside the Router for display purposes.
    """
    data_intents = ["get_customer_info", "get_customer_history", "update_email", "list_customers"]
    if intent in data_intents:
        return "Customer Data Agent (Port 8101)"
    return "Support Agent (Port 8102)"

# ---------------------------------------------------------
# Output Formatting Logic
# ---------------------------------------------------------
def print_separator(char="-", length=70):
    print(char * length)

def format_agent_response(result_item):
    """
    Parses a single result from the Router to display it neatly.
    """
    intent = result_item.get("intent", "Unknown")
    data = result_item.get("data")
    handoff_target = get_handoff_target(intent)
    
    # 1. Show LLM Classification & Handoff
    print(f"   [LLM CLASSIFICATION] Detected Intent: {intent}")
    print(f"   [ROUTER HANDOFF]     Routing Task To: {handoff_target}")
    
    # 2. Show Execution Results
    if isinstance(data, dict):
        answer_text = data.get("answer_text")
        
        # If there is a verbal answer (from Support Agent LLM)
        if answer_text:
            print(f"   [AGENT RESPONSE]     \"{answer_text}\"")
            
            # Show underlying data operation if exists (excluding the text)
            data_to_show = {k: v for k, v in data.items() if k != "answer_text"}
            if data_to_show:
                print(f"   [DATA OPERATION]     {json.dumps(data_to_show, indent=None)}")
        else:
            # Pure data response (from Data Agent)
            print(f"   [DATA RETRIEVED]     {json.dumps(data, indent=None)}")
            
    elif isinstance(data, list):
        print(f"   [DATA RETRIEVED]     List containing {len(data)} items")
        # Print first item as preview
        if len(data) > 0:
            print(f"                        Item 1: {json.dumps(data[0], indent=None)}")
            if len(data) > 1:
                print(f"                        ... {len(data)-1} more items")
    else:
        print(f"   [RAW OUTPUT]         {data}")
    
    print("") # Empty line for spacing

# ---------------------------------------------------------
# Main Execution Loop
# ---------------------------------------------------------
def run_scenario(scenario):
    name = scenario["name"]
    desc = scenario["desc"]
    payload = scenario["payload"]

    print_separator("=")
    print(f"TEST: {name}")
    print(f"Goal: {desc}")
    print(f"User Input: \"{payload['text']}\"")
    print_separator("=")

    try:
        start_time = time.time()
        # 30s timeout to allow for LLM inference on free tier
        response = requests.post(ROUTER_URL, json=payload, timeout=30)
        duration = time.time() - start_time

        if response.status_code == 200:
            json_resp = response.json()
            results = json_resp.get("results", [])
            
            print(f"STATUS: Success (Time: {duration:.2f}s)")
            print_separator("-")
            
            if not results:
                print("  [!] No results returned from agents.")
            
            for item in results:
                format_agent_response(item)
                
        else:
            print(f"STATUS: HTTP Error {response.status_code}")
            print(f"Error Message: {response.text}")

    except requests.exceptions.ConnectionError:
        print("STATUS: Connection Error")
        print("Details: Is the Router Agent running on port 8100?")
    except requests.exceptions.ReadTimeout:
        print("STATUS: Timeout")
        print("Details: The agents/LLM took too long to respond.")
    except Exception as e:
        print(f"STATUS: Script Error")
        print(f"Details: {e}")

    # 3 Second Delay
    print("Waiting 3 seconds before next test...\n")
    time.sleep(3)

if __name__ == "__main__":
    print("\nStarting Multi-Agent System Tests...\n")
    for s in scenarios:
        run_scenario(s)
    print("All scenarios completed.")
    