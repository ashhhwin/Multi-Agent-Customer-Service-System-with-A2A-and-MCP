import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any

# ------------------------
# DB connection
# ------------------------
def connect_db(path: str) -> sqlite3.Connection:
    """Return a sqlite3 connection with row factory as dict."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

# ------------------------
# Customers
# ------------------------
def fetch_customer(db_path: str, cust_id: int) -> Optional[Dict[str, Any]]:
    conn = connect_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE id = ?", (cust_id,))
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None

def fetch_customers(db_path: str, status_filter: Optional[str] = None,
                    tier_filter: Optional[str] = None, max_records: Optional[int] = None) -> List[Dict[str, Any]]:
    conn = connect_db(db_path)
    cursor = conn.cursor()

    base_query = "SELECT * FROM customers"
    conditions = []
    params: List[Any] = []

    if status_filter:
        if status_filter not in ("active", "disabled"):
            raise ValueError("Status must be 'active' or 'disabled'.")
        conditions.append("status = ?")
        params.append(status_filter)

    if tier_filter:
        if tier_filter not in ("standard", "premium", "enterprise"):
            raise ValueError("Tier must be one of 'standard', 'premium', 'enterprise'.")
        conditions.append("tier = ?")
        params.append(tier_filter)

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    if max_records:
        base_query += " LIMIT ?"
        params.append(max_records)

    cursor.execute(base_query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def modify_customer(db_path: str, cust_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update customer fields. Expects payload key `data` (not `updates`)."""
    allowed_keys = {"name", "email", "phone", "status", "tier", "billing_info"}

    for key in data:
        if key not in allowed_keys:
            raise ValueError(f"Invalid update field: {key}")

    if "status" in data and data["status"] not in ("active", "disabled"):
        raise ValueError("Status must be 'active' or 'disabled'.")
    if "tier" in data and data["tier"] not in ("standard", "premium", "enterprise"):
        raise ValueError("Tier must be one of 'standard', 'premium', 'enterprise'.")

    conn = connect_db(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM customers WHERE id = ?", (cust_id,))
    if not cursor.fetchone():
        conn.close()
        raise ValueError("Customer not found.")

    set_expr = ", ".join(f"{k} = ?" for k in data)
    values = list(data.values())
    values.append(datetime.utcnow())
    values.append(cust_id)

    cursor.execute(f"""
        UPDATE customers
        SET {set_expr}, updated_at = ?
        WHERE id = ?
    """, tuple(values))

    conn.commit()
    cursor.execute("SELECT * FROM customers WHERE id = ?", (cust_id,))
    updated = dict(cursor.fetchone())
    conn.close()
    return updated

# ------------------------
# Tickets
# ------------------------
def add_ticket(db_path: str, cust_id: int, issue_text: str, priority_level: str) -> Dict[str, Any]:
    if priority_level not in ("low", "medium", "high"):
        raise ValueError("Priority must be one of 'low', 'medium', 'high'.")

    conn = connect_db(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM customers WHERE id = ?", (cust_id,))
    if not cursor.fetchone():
        conn.close()
        raise ValueError("Customer does not exist.")

    cursor.execute("""
        INSERT INTO tickets (customer_id, issue, status, priority, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (cust_id, issue_text, "open", priority_level, datetime.utcnow()))

    conn.commit()
    ticket_id = cursor.lastrowid

    cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    ticket = dict(cursor.fetchone())
    conn.close()
    return ticket

def fetch_customer_history(db_path: str, cust_id: int) -> Dict[str, Any]:
    conn = connect_db(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM customers WHERE id = ?", (cust_id,))
    cust = cursor.fetchone()
    if not cust:
        conn.close()
        raise ValueError("Customer not found.")

    cursor.execute("SELECT * FROM tickets WHERE customer_id = ?", (cust_id,))
    tickets = [dict(t) for t in cursor.fetchall()]

    conn.close()
    return {"customer": dict(cust), "tickets": tickets}

def fetch_tickets(db_path: str, cust_ids: List[int], status_filter: Optional[str] = None,
                  priority_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """List tickets for multiple customers, with optional status & priority filters."""
    if not cust_ids:
        return []

    conn = connect_db(db_path)
    cursor = conn.cursor()

    placeholders = ",".join("?" * len(cust_ids))
    query = f"SELECT * FROM tickets WHERE customer_id IN ({placeholders})"
    params: List[Any] = list(cust_ids)

    if status_filter:
        if status_filter not in ("open", "in_progress", "resolved"):
            raise ValueError("Invalid ticket status.")
        query += " AND status = ?"
        params.append(status_filter)

    if priority_filter:
        if priority_filter not in ("low", "medium", "high"):
            raise ValueError("Invalid ticket priority.")
        params.append(priority_filter)
        query += " AND priority = ?"

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ------------------------
# Tool aliases for MCP server
# ------------------------
get_customer = fetch_customer
list_customers = fetch_customers
update_customer = modify_customer
create_ticket = add_ticket
get_customer_history = fetch_customer_history

def list_tickets_for_customers(db_path: str, cust_ids: List[int], status=None, priority=None):
    """
    MCP-friendly wrapper for fetch_tickets().
    Allows 'status' and 'priority' keyword arguments instead of 'status_filter'/'priority_filter'.
    """
    return fetch_tickets(db_path, cust_ids, status_filter=status, priority_filter=priority)