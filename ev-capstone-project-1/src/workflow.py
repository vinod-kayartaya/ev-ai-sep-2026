"""
LangGraph workflow builder for Enterprise Operations Assistant.
Orchestrates:
- Supervisor Agent
- Complaint Investigation Agent
- Reconciliation Agent
- Resolution Agent
- Human-in-the-Loop Approval Interruption
- Execution and Secure Audit Logging
- Langfuse Observability
"""

from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from langfuse import observe
from src.state import AgentState
from src.agents.investigation import investigation_agent
from src.agents.reconciliation import reconciliation_agent
from src.agents.resolution import resolution_agent
from src.agents.supervisor import supervisor_agent, route_supervisor
from src.tools.db_tools import create_financial_adjustment, update_adjustment_status
from src.tools.audit_tools import log_resolution
from src.config import get_langfuse_callback


@observe(name="Human_Approval_Node")
def human_approval_node(state: AgentState) -> Dict[str, Any]:
    """
    Human-in-the-Loop Node.
    Pauses execution for supervisor approval before executing any financial adjustment.
    """
    status = state.get("approval_status", "NOT_REQUIRED")
    if status == "PENDING":
        # Present human supervisor with investigation, reconciliation and adjustment summary
        interruption_payload = {
            "type": "SUPERVISOR_APPROVAL_REQUIRED",
            "customer_id": state.get("customer_id"),
            "invoice_id": state.get("invoice_id"),
            "internal_amount": state.get("invoice_data", {}).get("invoice_amount") if state.get("invoice_data") else None,
            "external_amount": state.get("external_billing_data", {}).get("amount") if state.get("external_billing_data") else None,
            "discrepancy": state.get("financial_adjustment_amount", 0.0),
            "finding": state.get("reconciliation_result", {}).get("details", "Billing discrepancy detected."),
            "recommended_action": state.get("recommended_resolution"),
            "reason": state.get("adjustment_reason", "Internal invoice differs from verified third-party billing."),
            "options": ["APPROVE", "REJECT"],
        }

        # Interrupt workflow and wait for supervisor decision
        decision = interrupt(interruption_payload)

        # Normalize decision
        decision_str = str(decision).strip().upper()
        if "APPROV" in decision_str:
            new_approval_status = "APPROVED"
        else:
            new_approval_status = "REJECTED"

        return {"approval_status": new_approval_status}

    return {"approval_status": status}


@observe(name="Execute_And_Log_Node")
def execute_and_log_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes financial adjustment if approved, records auditable log, and constructs final response.
    """
    customer_id = state.get("customer_id") or "UNKNOWN"
    invoice_id = state.get("invoice_id")
    complaint = state.get("complaint", "")
    investigation_summary = state.get("investigation_summary", "")
    reconciliation = state.get("reconciliation_result") or {}
    reconciliation_details = reconciliation.get("details", "")
    recommended_res = state.get("recommended_resolution", "")
    adj_amount = state.get("financial_adjustment_amount", 0.0)
    approval_status = state.get("approval_status", "NOT_REQUIRED")

    adj_id = None
    if approval_status == "APPROVED" and adj_amount > 0:
        # 1. Create financial adjustment record in DB
        adj_tool_res = create_financial_adjustment.invoke({
            "customer_id": customer_id,
            "invoice_id": invoice_id or "N/A",
            "amount": adj_amount,
            "reason": state.get("adjustment_reason") or "Supervisor approved adjustment",
        })
        adj_id = adj_tool_res.get("adjustment_id")

        # 2. Update status to Approved
        if adj_id:
            update_adjustment_status.invoke({
                "adjustment_id": adj_id,
                "status": "Approved",
            })
        final_status = "Approved - Financial Adjustment Executed"
        approval_display = f"Approved (Adjustment ID: {adj_id})"

    elif approval_status == "REJECTED":
        final_status = "Rejected - Financial Adjustment Denied by Supervisor"
        approval_display = "Rejected by Supervisor"

    elif state.get("requires_financial_adjustment") and approval_status == "PENDING":
        final_status = "Pending Supervisor Approval"
        approval_display = "Supervisor approval required"

    elif reconciliation.get("status") == "MATCH":
        final_status = "Resolved - Verified Accurate Billing"
        approval_display = "Not Required"

    else:
        final_status = "Closed - Investigation Concluded"
        approval_display = "Not Required"

    # 3. Log resolution to auditable database table
    log_res = log_resolution.invoke({
        "customer_id": customer_id,
        "complaint": complaint,
        "invoice_id": invoice_id,
        "investigation_result": investigation_summary,
        "reconciliation_result": reconciliation_details,
        "resolution": recommended_res,
        "financial_adjustment_amount": adj_amount if approval_status == "APPROVED" else 0.0,
        "approval_decision": approval_status,
        "final_status": final_status,
    })

    # 4. Construct Capstone-compliant final response format (Section 13)
    diff_val = reconciliation.get("difference", adj_amount)
    finding_text = reconciliation.get("details") or investigation_summary

    final_response = (
        "Complaint Investigation Completed\n\n"
        f"Customer: {customer_id}\n"
        f"Invoice: {invoice_id or 'N/A'}\n\n"
        f"Finding:\n{finding_text}\n\n"
        f"Discrepancy:\n₹{diff_val:,.2f}\n\n"
        f"Recommended Resolution:\n{recommended_res}\n\n"
        f"Approval:\n{approval_display}\n\n"
        f"Status:\n{final_status}"
    )

    return {
        "adjustment_id": adj_id,
        "final_response": final_response,
        "approval_status": approval_status,
    }


def build_operations_workflow(checkpointer: Optional[Any] = None):
    """
    Constructs and compiles the StateGraph workflow with Supervisor orchestration.
    """
    builder = StateGraph(AgentState)

    # Register Nodes
    builder.add_node("supervisor_agent", supervisor_agent)
    builder.add_node("investigation_agent", investigation_agent)
    builder.add_node("reconciliation_agent", reconciliation_agent)
    builder.add_node("resolution_agent", resolution_agent)
    builder.add_node("human_approval", human_approval_node)
    builder.add_node("execute_and_log", execute_and_log_node)

    # Flow starts at Supervisor
    builder.add_edge(START, "supervisor_agent")

    # Supervisor conditional routing
    builder.add_conditional_edges(
        "supervisor_agent",
        route_supervisor,
        {
            "investigation_agent": "investigation_agent",
            "reconciliation_agent": "reconciliation_agent",
            "resolution_agent": "resolution_agent",
            "human_approval": "human_approval",
            "execute_and_log": "execute_and_log",
            "END": END,
        },
    )

    # Specialized agents loop back to Supervisor for next determination
    builder.add_edge("investigation_agent", "supervisor_agent")
    builder.add_edge("reconciliation_agent", "supervisor_agent")
    builder.add_edge("resolution_agent", "supervisor_agent")
    builder.add_edge("human_approval", "supervisor_agent")
    builder.add_edge("execute_and_log", "supervisor_agent")

    if checkpointer is None:
        checkpointer = MemorySaver()

    return builder.compile(checkpointer=checkpointer)
