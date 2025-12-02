# Multi-Agent Customer Service System (A2A + MCP + LLM)

## Overview

A distributed multi-agent system designed to automate customer service workflows. The architecture leverages **Agent-to-Agent (A2A)** coordination for task delegation, the **Model Context Protocol (MCP)** for secure database access, and **Large Language Models (LLM)** for intelligent intent classification and natural language generation.

The system orchestrates three autonomous agents to handle complex customer queries, data retrieval, and ticket management using a combination of deterministic tools and generative AI.

### Architecture

* **Router Agent (Port 8100):** Orchestrator. Uses an LLM (via Hugging Face API) to analyze natural language queries, extract entities, and route tasks to the appropriate specialist.
* **Customer Data Agent (Port 8101):** Data Specialist. Interfaces with the MCP Server to fetch and update customer records.
* **Support Agent (Port 8102):** Support Specialist. Manages ticket creation and status checks. Uses an LLM to generate concise, conversational responses based on tool outputs.
* **MCP Server (Stdio):** Database Interface. Exposes SQLite tools via `FastMCP` over standard input/output.

## Prerequisites

* Python 3.10+

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

**Important:** You must set your Hugging Face Token for the agents to function intelligently.

1.  **Set API Token:**

2.  **Launch Agents:**
    Open three separate terminal windows (ensure the venv is active and the token is set in each):

    * **Terminal 1 (Data):** `python -m agents.customer_data_agent`
    * **Terminal 2 (Support):** `python -m agents.support_agent`
    * **Terminal 3 (Router):** `python -m agents.router_agent`

## Testing & Validation

### 1. End-to-End Scenarios

Execute the integration test suite to verify agent coordination, task allocation, and negotiation flows. This includes testing natural language inputs (e.g., "I want my money back") to verify LLM intent classification.

```bash
python -m tests.run_scenarios
