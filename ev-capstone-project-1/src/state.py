"""
LangGraph state definitions for the Enterprise Operations Assistant.
"""

from typing import TypedDict, Dict, Any, Optional, Sequence, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Central state tracked across the LangGraph multi-agent workflow.
    """
    # Conversation message history
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # User complaint input
    complaint: str

    # Extracted entity IDs
    customer_id: Optional[str]
    invoice_id: Optional[str]

    # Investigation data
    customer_data: Optional[Dict[str, Any]]
    invoice_data: Optional[Dict[str, Any]]
    external_billing_data: Optional[Dict[str, Any]]
    investigation_summary: Optional[str]

    # Reconciliation findings
    reconciliation_result: Optional[Dict[str, Any]]

    # Resolution & Financial Adjustment
    recommended_resolution: Optional[str]
    requires_financial_adjustment: bool
    financial_adjustment_amount: float
    adjustment_reason: Optional[str]
    adjustment_id: Optional[str]

    # Human-in-the-Loop approval state
    # Values: 'NOT_REQUIRED', 'PENDING', 'APPROVED', 'REJECTED'
    approval_status: str

    # Supervisor routing control
    next_step: Optional[str]

    # Final formatted response for the user
    final_response: Optional[str]

    # Error handling
    error: Optional[str]
