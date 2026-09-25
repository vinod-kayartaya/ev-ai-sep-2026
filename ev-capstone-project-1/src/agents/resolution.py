"""
Resolution Agent.
Responsible for:
- Reviewing investigation and reconciliation findings
- Determining an appropriate resolution
- Determining whether a financial adjustment is required
- Preparing supervisor review details when human approval is required
"""

from typing import Dict, Any
from langfuse import observe
from src.state import AgentState


@observe(name="Resolution_Agent")
def resolution_agent(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates reconciliation results and formulates the resolution recommendation.
    Sets flags for Human-in-the-Loop financial approval.
    """
    reconciliation = state.get("reconciliation_result") or {}
    status = reconciliation.get("status", "UNKNOWN")
    customer_id = state.get("customer_id")
    invoice_id = state.get("invoice_id")
    customer_data = state.get("customer_data")
    invoice_data = state.get("invoice_data")

    # 1. Handle Invalid/Missing Records
    if not customer_id or (customer_id and not customer_data) or status in ["NOT_FOUND", "INTERNAL_NOT_FOUND", "NOT_APPLICABLE"]:
        missing_entity = "Customer or Invoice" if not customer_id or not invoice_id else "Record"
        res_text = (
            f"Invalid or unverified {missing_entity} details. Internal investigation confirms that the requested "
            f"customer ID ('{customer_id}') or invoice ID ('{invoice_id}') does not exist in our operational records. "
            f"No financial adjustment can be processed without valid customer identification."
        )
        return {
            "recommended_resolution": res_text,
            "requires_financial_adjustment": False,
            "financial_adjustment_amount": 0.0,
            "adjustment_reason": None,
            "approval_status": "NOT_REQUIRED",
        }

    # 2. Handle Match (No Discrepancy)
    if status == "MATCH":
        internal_amt = reconciliation.get("internal_amount", 0.0)
        res_text = (
            f"Internal invoice records and the third-party billing gateway both confirm an identical "
            f"amount of ₹{internal_amt:,.2f}. No billing discrepancy detected. No financial adjustment is required. "
            f"Close ticket and reassure customer of correct charge."
        )
        return {
            "recommended_resolution": res_text,
            "requires_financial_adjustment": False,
            "financial_adjustment_amount": 0.0,
            "adjustment_reason": None,
            "approval_status": "NOT_REQUIRED",
        }

    # 3. Handle Duplicate Charge
    if status == "DUPLICATE_CHARGE_DETECTED":
        dup_amt = reconciliation.get("financial_impact", 0.0)
        reason = "Duplicate invoice charge recorded for the same billing period"
        res_text = (
            f"Duplicate billing verified: Customer was charged multiple times for the same transaction. "
            f"Issue a financial adjustment / refund of ₹{dup_amt:,.2f} to reconcile the account balance."
        )
        return {
            "recommended_resolution": res_text,
            "requires_financial_adjustment": True,
            "financial_adjustment_amount": dup_amt,
            "adjustment_reason": reason,
            "approval_status": "PENDING",
        }

    # 4. Handle Discrepancy / Overcharge
    if status == "DISCREPANCY_DETECTED":
        diff = reconciliation.get("difference", 0.0)
        reason = "Internal invoice amount differs from verified third-party billing amount"
        res_text = f"Create a ₹{diff:,.2f} financial adjustment for the customer."
        return {
            "recommended_resolution": res_text,
            "requires_financial_adjustment": True,
            "financial_adjustment_amount": diff,
            "adjustment_reason": reason,
            "approval_status": "PENDING",
        }

    # 5. Default / Fallback
    res_text = "Manual investigation required by operations lead."
    return {
        "recommended_resolution": res_text,
        "requires_financial_adjustment": False,
        "financial_adjustment_amount": 0.0,
        "adjustment_reason": None,
        "approval_status": "NOT_REQUIRED",
    }
