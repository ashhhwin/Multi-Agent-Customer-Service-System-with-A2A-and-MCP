import os
import sys
import json
import subprocess
from typing import Optional, List
from mcp.server.fastmcp import FastMCP

# Import db_utils handling both module and script execution contexts
try:
    from . import db_utils
except ImportError:
    import db_utils

# Initialize the FastMCP Server
mcp = FastMCP("CustomerSupport", dependencies=["sqlite3"])

# Configuration
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_FILE = os.path.join(PROJECT_ROOT, "support.db")

# ---------------------------------------------------------
# Tool Definitions
# ---------------------------------------------------------

@mcp.tool()
def get_customer(customer_id: int) -> str:
    """Retrieves a customer by their ID."""
    result = db_utils.get_customer(DB_FILE, customer_id)
    return json.dumps(result)

@mcp.tool()
def list_customers(status: Optional[str] = None, tier: Optional[str] = None, limit: Optional[int] = 10) -> str:
    """Lists customers with optional filters for status or tier."""
    
    # --- CRITICAL FIX: Normalize Inputs ---
    # 1. Force lowercase to match DB constraints ('Active' -> 'active')
    if status:
        status = status.lower().strip()
        # 2. Safety check: If invalid status, default to None to avoid crash
        if status not in ['active', 'disabled']:
            status = None

    if tier:
        tier = tier.lower().strip()
        if tier not in ['standard', 'premium', 'enterprise']:
            tier = None

    # 3. Map arguments correctly to db_utils signature
    result = db_utils.list_customers(
        DB_FILE, 
        status_filter=status, 
        tier_filter=tier, 
        max_records=limit
    )
    return json.dumps(result)

@mcp.tool()
def update_customer(customer_id: int, data: dict) -> str:
    """Updates customer details (email, tier, billing_info)."""
    # Normalize inputs inside the data dict
    if "status" in data and isinstance(data["status"], str):
        data["status"] = data["status"].lower()
    if "tier" in data and isinstance(data["tier"], str):
        data["tier"] = data["tier"].lower()

    result = db_utils.update_customer(DB_FILE, customer_id, data)
    return json.dumps(result)

@mcp.tool()
def create_ticket(customer_id: int, issue: str, priority: str) -> str:
    """Creates a support ticket for a customer."""
    # Force priority to lowercase
    if priority:
        priority = priority.lower().strip()
        
    result = db_utils.create_ticket(DB_FILE, customer_id, issue, priority)
    return json.dumps(result)

@mcp.tool()
def get_customer_history(customer_id: int) -> str:
    """Retrieves ticket history for a specific customer."""
    result = db_utils.get_customer_history(DB_FILE, customer_id)
    return json.dumps(result)

@mcp.tool()
def list_tickets(customer_ids: List[int], status: Optional[str] = None, priority: Optional[str] = None) -> str:
    """Lists tickets for specific customers with optional filters."""
    # Normalize inputs
    if status: status = status.lower()
    if priority: priority = priority.lower()

    result = db_utils.list_tickets_for_customers(DB_FILE, customer_ids, status=status, priority=priority)
    return json.dumps(result)

@mcp.tool()
def reset_db() -> str:
    """Resets the database to initial state using database_setup.py."""
    script_path = os.path.join(os.path.dirname(__file__), "database_setup.py")
    if os.path.exists(script_path):
        subprocess.run([sys.executable, script_path], input=b"y\ny\n")
        return "Database reset completed."
    return "Error: database_setup.py not found."

if __name__ == "__main__":
    mcp.run()