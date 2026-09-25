"""
Reconciliation Agent.
Responsible for:
- Comparing internal and external billing information
- Identifying discrepancies (amount mismatch, duplicate billing, missing invoices)
- Determining financial impact
- Producing structured reconciliation results
"""

from typing import Dict, Any
from langfuse import observe
from src.tools.reconciliation_tools import reconcile_invoice
from src.state import AgentState


@observe(name="Reconciliation_Agent")
def reconciliation_agent(state: AgentState) -> Dict[str, Any]:
    """
    Executes reconciliation between internal DB records and external billing gateway.
    """
    invoice_id = state.get("invoice_id")
    customer_id = state.get("customer_id")
    invoice_data = state.get("invoice_data")
    external_data = state.get("external_billing_data")

    # If neither invoice_id exists nor any invoice was found
    if not invoice_id:
        result = {
            "status": "NOT_APPLICABLE",
            "message": "No valid invoice found to reconcile.",
            "discrepancy_detected": False,
            "financial_impact": 0.0,
            "difference": 0.0,
            "internal_amount": 0.0,
            "external_amount": 0.0,
            "details": "Reconciliation skipped: Missing invoice identifier.",
        }
        return {"reconciliation_result": result}

    # Execute reconcile tool
    reconciliation = reconcile_invoice.invoke({"invoice_id": invoice_id})

    # If tool reported match or mismatch, format structured text output
    internal_amt = reconciliation.get("internal_amount", invoice_data.get("invoice_amount", 0.0) if invoice_data else 0.0)
    external_amt = reconciliation.get("external_amount", external_data.get("amount", 0.0) if external_data else 0.0)
    difference = reconciliation.get("difference", 0.0)
    status_str = reconciliation.get("status", "UNKNOWN")

    formatted_summary = (
        f"Internal Invoice Amount : ₹{internal_amt:,.2f}\n"
        f"External Billing Amount : ₹{external_amt:,.2f}\n"
        f"Difference              : ₹{difference:,.2f}\n"
        f"Status                  : {status_str}"
    )

    reconciliation["formatted_summary"] = formatted_summary

    return {"reconciliation_result": reconciliation}
