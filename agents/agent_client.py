import uuid
import time
import json
import logging
import sys
import os
import requests
import asyncio
from datetime import datetime

# MCP SDK Imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ---------------------------------------------------------
# 1. Agent Card & A2A Schema
# ---------------------------------------------------------

def create_a2a_message(sender_id, recipient_id, intent, content, msg_type="request", corr_id=None):
    """Constructs a compliant A2A message."""
    return {
        "message_id": str(uuid.uuid4()),
        "from": sender_id,
        "to": recipient_id,
        "type": msg_type,
        "intent": intent,
        "payload": content if content else {},
        "correlation_id": corr_id or str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat()
    }

def check_message_schema(message: dict):
    required = ["message_id", "from", "to", "type", "intent", "payload", "correlation_id"]
    missing = [f for f in required if f not in message]
    if missing:
        raise ValueError(f"Invalid A2A Message. Missing: {missing}")
    return True

def generate_error_response(orig_message, error_text):
    return create_a2a_message(
        sender_id=orig_message.get("to", "unknown"),
        recipient_id=orig_message.get("from", "unknown"),
        intent=orig_message.get("intent", "error"),
        msg_type="error",
        corr_id=orig_message.get("correlation_id"),
        content={"error": str(error_text)}
    )

# ---------------------------------------------------------
# 2. Agent Connector (The Client Logic)
# ---------------------------------------------------------
class AgentConnector:
    def __init__(self, timeout_sec=5, max_attempts=3):
        self.timeout = timeout_sec
        self.max_attempts = max_attempts
        # Determine path to MCP server app
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
    # --- A2A Communication (HTTP between Agents) ---
    def send_message(self, target_url, message: dict):
        """Sends an A2A message to another agent via HTTP."""
        try:
            check_message_schema(message)
            logging.info(f"[A2A-SEND] To: {target_url} | Intent: {message.get('intent')}")
            
            resp = requests.post(f"{target_url}/a2a", json=message, timeout=self.timeout)
            
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"status": "error", "error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            logging.error(f"[A2A-FAIL] {e}")
            return {"status": "error", "error": str(e)}

    # --- MCP Tool Invocation (Stdio to MCP Server) ---
    async def invoke_tool(self, tool_name: str, arguments: dict):
        """
        Connects to the MCP server via Stdio, calls the tool, and returns the result.
        This is the 'Independent MCP Client' logic required by the professor.
        """
        logging.info(f"[MCP-START] Calling {tool_name}...")

        # Server Parameters: Run 'python -m mcp_server.app'
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.app"],
            env=os.environ.copy() # Pass current env (PATH, etc)
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # 1. Initialize
                    await session.initialize()
                    
                    # 2. Call Tool
                    # Note: We assume the MCP server returns a JSON string, so we parse it.
                    result = await session.call_tool(tool_name, arguments)
                    
                    # 3. Parse Result (Standard MCP tools return a list of content blocks)
                    if result and hasattr(result, 'content') and result.content:
                        text_content = result.content[0].text
                        try:
                            # Our tools return JSON strings, so we parse them back to dicts
                            return json.loads(text_content)
                        except:
                            return text_content
                    
                    return {"status": "error", "data": "No content returned from tool"}

        except Exception as e:
            logging.error(f"[MCP-ERROR] {e}")
            return {"status": "error", "error": str(e)}

    # Helper wrapper for synchronous agents calling async MCP
    def invoke_tool_sync(self, tool_name, arguments):
        """Helper to run async tool call in sync context"""
        return asyncio.run(self.invoke_tool(tool_name, arguments))