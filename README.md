# Multi-Agent Customer Service System (A2A + MCP)

## Overview

A distributed multi-agent system designed to automate customer service workflows. The architecture leverages **Agent-to-Agent (A2A)** coordination for task delegation and the **Model Context Protocol (MCP)** for secure, standardized database access.

The system orchestrates three autonomous agents to handle complex customer queries, data retrieval, and ticket management.

### Architecture

* **Router Agent (Port 8100):** Orchestrator. Analyzes query intent and routes tasks to the appropriate specialist.
* **Customer Data Agent (Port 8101):** Data Specialist. Interfaces with the MCP Server to fetch and update customer records.
* **Support Agent (Port 8102):** Support Specialist. Manages ticket creation, status checks, and escalation logic.
* **MCP Server (Stdio):** Database Interface. Exposes SQLite tools via `FastMCP` over standard input/output.

## Prerequisites

* Python 3.10+
* `pip`
* Node.js & npm (Optional; required only for MCP Inspector validation)

## Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd multi_agent_customer_service
    ```

2.  **Setup Virtual Environment:**

    ```bash
    python -m venv venv
    # Mac/Linux:
    source venv/bin/activate
    # Windows:
    venv\Scripts\activate
    ```

3.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Initialize Database:**
    Generates `support.db` and seeds initial data.

    ```bash
    python -m mcp_server.database_setup
    ```
    *Confirm with `y` when prompted.*

## Usage

Launch each agent in a separate terminal window:

1.  **Data Agent:** `python -m agents.customer_data_agent`
2.  **Support Agent:** `python -m agents.support_agent`
3.  **Router Agent:** `python -m agents.router_agent`

## Testing & Validation

### 1. End-to-End Scenarios

Execute the integration test suite to verify agent coordination, task allocation, and negotiation flows.

```bash
python -m tests.run_scenarios
