# Enterprise Operations Assistant

An end-to-end multi-agent AI assistant for customer operations teams to investigate billing disputes, reconcile discrepancies with internal and third-party systems, recommend resolutions, enforce human-in-the-loop supervisor approvals for financial adjustments, and securely log auditable outcomes.

Built with **Python**, **LangChain**, **LangGraph**, and **Langfuse**.

---

## 1. Solution Architecture

The system uses a stateful, graph-based multi-agent supervisor pattern implemented with **LangGraph**:

```
                         +-----------------------------+
                         |      Customer Complaint     |
                         +--------------+--------------+
                                        |
                                        v
                         +-----------------------------+
                         |       Supervisor Agent      | <------+
                         +--------------+--------------+        |
                                        | (route)               |
         +------------------------------+-----------------------+
         |                              |                       |
         v                              v                       v
+------------------+         +--------------------+   +-------------------+
|  Investigation   |         |   Reconciliation   |   | Resolution Agent  |
|      Agent       |         |       Agent        |   | (Proposes Action) |
+--------+---------+         +---------+----------+   +---------+---------+
         |                             |                        |
         | Query DB & External API     | Calculate Discrepancy  | Adjustment needed?
         v                             v                        v
+------------------+         +--------------------+   +-------------------+
| DB / Mock API    |         | Internal vs Ext    |   | Human-in-the-Loop |
| (SQLite / REST)  |         | Comparison Result  |   | Supervisor Gate   |
+------------------+         +--------------------+   +---------+---------+
                                                                |
                                                      [Approve] / [Reject]
                                                                v
                                                      +-------------------+
                                                      | Execute Action &  |
                                                      | Audit Log to DB   |
                                                      +-------------------+
```

### Key Workflow Highlights
1. **Dynamic Supervisor Coordination**: The supervisor agent inspects the state after each step and dynamically determines the next specialized agent to execute.
2. **Stateful Graph Execution with Memory**: State is managed via `AgentState` and persisted across execution steps using LangGraph's checkpointer (`MemorySaver`).
3. **Human-in-the-Loop Interruption**: When a financial adjustment is flagged, the workflow halts using LangGraph's `interrupt(...)`. A supervisor reviews the finding and recommendation and issues an `APPROVE` or `REJECT` decision to resume execution.
4. **Auditable Logging**: Completed resolutions and approval decisions are written to the SQLite `resolution_logs` table.
5. **Observability**: End-to-end traces of LLM calls, tool executions, agent routing, and state transitions are streamed to Langfuse.

---

## 2. Directory Structure

```text
ev-capstone-project-1/
├── .env                              # Environment credentials (OpenAI, Langfuse)
├── requirements.txt                  # Python dependencies
├── setup_db.py                       # SQLite database initialization & seed script
├── database/
│   └── operations.db                 # SQLite database (customers, invoices, adjustments, resolution_logs)
├── mock_service/
│   └── mock_billing_api.py           # FastAPI mock third-party billing REST API
├── src/
│   ├── __init__.py
│   ├── config.py                     # Environment and LLM/Langfuse configuration
│   ├── db.py                         # SQLite query & persistence layer
│   ├── state.py                      # LangGraph AgentState TypedDict definition
│   ├── tools/                        # Enterprise operations tools
│   │   ├── __init__.py
│   │   ├── db_tools.py               # get_customer, get_invoice, get_customer_invoices, adjustments
│   │   ├── billing_tools.py          # get_external_billing (REST API + direct fallback)
│   │   ├── reconciliation_tools.py   # reconcile_invoice
│   │   └── audit_tools.py            # log_resolution
│   ├── agents/                       # Specialized agents
│   │   ├── __init__.py
│   │   ├── supervisor.py             # Supervisor agent & conditional router
│   │   ├── investigation.py          # Complaint Investigation agent
│   │   ├── reconciliation.py         # Reconciliation agent
│   │   └── resolution.py             # Resolution agent
│   └── workflow.py                   # LangGraph StateGraph builder, HITL interrupt, & checkpointer
├── run_assistant.py                  # CLI runner for interactive / automated complaint handling
└── README.md                         # Project documentation
```

---

## 3. Setup & Installation

### Prerequisites
- Python 3.10+
- (Optional) Local or remote Langfuse server (e.g. `http://localhost:3000`)

### Step 1: Create Virtual Environment and Install Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Create or verify `.env`:
```ini
# Langfuse Observability Configuration
LANGFUSE_SECRET_KEY="sk-lf-..."
LANGFUSE_PUBLIC_KEY="pk-lf-..."
LANGFUSE_BASE_URL="http://localhost:3000"
LANGFUSE_HOST="http://localhost:3000"

# OpenAI Configuration
OPENAI_API_KEY="sk-proj-..."
OPENAI_MODEL_NAME="gpt-4o-mini"

# Mock Service Configuration
MOCK_API_PORT=8000
DATABASE_PATH="database/operations.db"
```

### Step 3: Initialize Database
```bash
python setup_db.py
```
This generates `database/operations.db` with sample records for customers (`C1024`–`C1028`) and invoices (`INV10045`–`INV10049`).

### Step 4: (Optional) Run Mock Billing REST API
The mock billing API can run as a standalone FastAPI service:
```bash
python mock_service/mock_billing_api.py
```
*Note: The tools automatically fall back to direct in-memory mock queries if the REST API server is offline.*

---

## 4. Agent Responsibilities

| Agent | Responsibility | Tools Used |
| :--- | :--- | :--- |
| **Supervisor Agent** | Coordinates workflow, evaluates completed steps, dynamically determines next agent, halts for human approval, triggers audit logging. | State router |
| **Complaint Investigation Agent** | Parses natural language complaints, extracts customer and invoice IDs, looks up internal DB, queries external billing gateway. | `get_customer`, `get_invoice`, `get_customer_invoices`, `get_external_billing` |
| **Reconciliation Agent** | Compares internal invoice amounts with external billing gateway, identifies discrepancies, detects duplicate charges, computes difference. | `reconcile_invoice` |
| **Resolution Agent** | Determines operational resolution, calculates required financial adjustments, prepares supervisor review details, flags `approval_status = PENDING`. | None (State analysis) |
| **Human-in-the-Loop Node** | Pauses execution via LangGraph `interrupt(...)` until authorized supervisor submits `APPROVE` or `REJECT`. | LangGraph `interrupt` & `Command(resume=...)` |
| **Execution & Audit Node** | Creates and updates financial adjustment records in DB upon approval, logs final audit record into `resolution_logs`. | `create_financial_adjustment`, `update_adjustment_status`, `log_resolution` |

---

## 5. Enterprise Tools Implemented

1. `get_customer(customer_id: str)`: Returns customer details (`name`, `email`, `account_status`) from `customers` table.
2. `get_invoice(invoice_id: str)`: Returns invoice records (`amount`, `status`, `invoice_date`) from `invoices` table.
3. `get_customer_invoices(customer_id: str)`: Returns all invoices for a given customer.
4. `get_external_billing(invoice_id: str)`: Queries the mock third-party billing REST API endpoint (`GET /billing/{invoice_id}`).
5. `reconcile_invoice(invoice_id: str)`: Reconciles internal and external records, calculating `status` (`MATCH`, `DISCREPANCY_DETECTED`, `DUPLICATE_CHARGE_DETECTED`, `NOT_FOUND`), difference, and financial impact.
6. `create_financial_adjustment(customer_id, invoice_id, amount, reason)`: Inserts a pending record into `adjustments` table.
7. `update_adjustment_status(adjustment_id, status)`: Updates adjustment to `Approved` or `Rejected`.
8. `log_resolution(...)`: Writes full auditable resolution log to `resolution_logs` table.

---

## 6. Running the Assistant

Run the assistant in interactive mode:
```bash
python run_assistant.py
```

The assistant runs in an endless loop, accepting natural language customer complaints one after another.

- To stop the assistant, simply type `exit`, `quit`, or press `Ctrl+C`.
- When a financial adjustment is flagged, the assistant pauses for supervisor approval (`APPROVE` or `REJECT`).


---

## 7. Sample Request and Response

### Sample Request
```text
"Customer C1024 has complained that they were charged ₹12,500 for their latest invoice, but the amount shown by the billing system is ₹10,000. Investigate the discrepancy and recommend an appropriate resolution."
```

### Human-in-the-Loop Interruption Screen
```text
======================================================================
HUMAN-IN-THE-LOOP: SUPERVISOR APPROVAL REQUIRED
======================================================================
Customer       : C1024
Invoice        : INV10045
Internal Amount: ₹12,500.00
External Amount: ₹10,000.00
Discrepancy    : ₹2,500.00

Finding:
Discrepancy detected: Internal amount ₹12,500.00 vs External amount ₹10,000.00. Difference is ₹2,500.00.

Recommended Action:
Create a ₹2,500.00 financial adjustment for the customer.

Reason:
Internal invoice amount differs from verified third-party billing amount
======================================================================

Enter decision [APPROVE / REJECT] (default: APPROVE): APPROVE
```

### Final Response Format
```text
======================================================================
FINAL OPERATIONAL SUMMARY
======================================================================
Complaint Investigation Completed

Customer: C1024
Invoice: INV10045

Finding:
Discrepancy detected: Internal amount ₹12,500.00 vs External amount ₹10,000.00. Difference is ₹2,500.00.

Discrepancy:
₹2,500.00

Recommended Resolution:
Create a ₹2,500.00 financial adjustment for the customer.

Approval:
Approved (Adjustment ID: ADJE46E48)

Status:
Approved - Financial Adjustment Executed
======================================================================
```

---

## 8. Automated Evaluation Suite

To run the full evaluation suite covering all 5 representative business scenarios:

```bash
python evaluate.py
```

### Evaluation Benchmark Results

| Scenario | Result | Accuracy | Latency |
| :--- | :---: | :---: | :---: |
| **Billing amount mismatch** (`INV10045`, diff ₹2,500) | **Pass** | **100%** | **7.8 sec** |
| **Duplicate charge** (`INV10046`, dup ₹3,000) | **Pass** | **100%** | **0.04 sec** |
| **Correct billing** (`INV10047`, match ₹7,500) | **Pass** | **100%** | **0.03 sec** |
| **Financial adjustment (HITL)** (`INV10048`, diff ₹3,500) | **Pass** | **100%** | **0.03 sec** |
| **Invalid customer/invoice** (`C9999` / `INV99999`) | **Pass** | **100%** | **0.03 sec** |

- **Overall Accuracy**: **100.0%**
- **Average Latency**: **1.59 sec**
- Full breakdown is stored in `evaluation_report.md` and `evaluation_results.json`.

---

## 9. Observability & Tracing with Langfuse

The system includes dual-layer Langfuse observability:
1. **`@observe` Decorators**:
   - Decorated entry-point runner: `@observe(name="Enterprise_Operations_Assistant")` on `process_complaint`.
   - Decorated specialized agents:
     - `@observe(name="Supervisor_Agent")` on `supervisor_agent`
     - `@observe(name="Investigation_Agent")` on `investigation_agent`
     - `@observe(name="Reconciliation_Agent")` on `reconciliation_agent`
     - `@observe(name="Resolution_Agent")` on `resolution_agent`
   - Decorated workflow nodes:
     - `@observe(name="Human_Approval_Node")` on `human_approval_node`
     - `@observe(name="Execute_And_Log_Node")` on `execute_and_log_node`
   - Decorated enterprise tools:
     - `@observe(name="get_customer")`
     - `@observe(name="get_invoice")`
     - `@observe(name="get_customer_invoices")`
     - `@observe(name="get_external_billing")`
     - `@observe(name="reconcile_invoice")`
     - `@observe(name="create_financial_adjustment")`
     - `@observe(name="update_adjustment_status")`
     - `@observe(name="log_resolution")`

2. **Langfuse LangChain CallbackHandler**:
   - Attached via `config={"callbacks": [langfuse_handler]}` to stream full LLM generation tokens, prompt structures, and graph state transitions.
   - When the Langfuse instance runs at `http://localhost:3000`, all traces are streamed directly.

