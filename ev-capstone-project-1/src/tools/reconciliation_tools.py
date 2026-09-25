"""
Reconciliation tool for comparing internal invoice and external billing records.
"""

from typing import Dict, Any, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langfuse import observe
from src.db import fetch_invoice, fetch_customer_invoices
from mock_service.mock_billing_api import query_mock_billing_direct


class ReconcileInvoiceInput(BaseModel):
    invoice_id: str = Field(description="The invoice ID to reconcile, e.g. INV10045")


@tool("reconcile_invoice", args_schema=ReconcileInvoiceInput)
@observe(name="reconcile_invoice")
def reconcile_invoice(invoice_id: str) -> Dict[str, Any]:
    """Compare internal invoice data against external billing records to identify discrepancies and financial impact."""
    clean_id = invoice_id.strip().upper()
    internal_rec = fetch_invoice(clean_id)
    external_rec = query_mock_billing_direct(clean_id)

    if not internal_rec and not external_rec:
        return {
            "status": "NOT_FOUND",
            "invoice_id": clean_id,
            "message": f"Invoice '{clean_id}' could not be found in internal or external records.",
            "discrepancy_detected": False,
            "financial_impact": 0.0,
        }

    if not internal_rec:
        return {
            "status": "INTERNAL_NOT_FOUND",
            "invoice_id": clean_id,
            "external_amount": external_rec.get("amount") if external_rec else 0.0,
            "message": f"Invoice '{clean_id}' exists in external billing but not in internal database.",
            "discrepancy_detected": True,
            "financial_impact": 0.0,
        }

    if not external_rec:
        return {
            "status": "EXTERNAL_NOT_FOUND",
            "invoice_id": clean_id,
            "internal_amount": internal_rec["invoice_amount"],
            "message": f"Invoice '{clean_id}' exists in internal database but is missing in external billing gateway.",
            "discrepancy_detected": True,
            "financial_impact": internal_rec["invoice_amount"],
        }

    internal_amount = float(internal_rec["invoice_amount"])
    external_amount = float(external_rec["amount"])
    diff = round(internal_amount - external_amount, 2)
    customer_id = internal_rec["customer_id"]

    # Check for potential duplicate internal billing for the same customer and amount
    all_customer_invoices = fetch_customer_invoices(customer_id)
    duplicates = [
        inv["invoice_id"]
        for inv in all_customer_invoices
        if inv["invoice_id"] != clean_id
        and inv["invoice_amount"] == internal_amount
        and inv["invoice_date"] == internal_rec["invoice_date"]
    ]

    is_duplicate = len(duplicates) > 0

    if is_duplicate:
        return {
            "status": "DUPLICATE_CHARGE_DETECTED",
            "customer_id": customer_id,
            "invoice_id": clean_id,
            "duplicate_invoice_ids": duplicates,
            "internal_amount": internal_amount,
            "external_amount": external_amount,
            "difference": internal_amount,
            "discrepancy_detected": True,
            "financial_impact": internal_amount,
            "details": f"Duplicate billing detected: Customer {customer_id} was charged twice (₹{internal_amount:,.2f}) on {internal_rec['invoice_date']}.",
        }

    if abs(diff) > 0.01:
        return {
            "status": "DISCREPANCY_DETECTED",
            "customer_id": customer_id,
            "invoice_id": clean_id,
            "internal_amount": internal_amount,
            "external_amount": external_amount,
            "difference": diff,
            "discrepancy_detected": True,
            "financial_impact": diff,
            "details": f"Discrepancy detected: Internal amount ₹{internal_amount:,.2f} vs External amount ₹{external_amount:,.2f}. Difference is ₹{diff:,.2f}.",
        }

    return {
        "status": "MATCH",
        "customer_id": customer_id,
        "invoice_id": clean_id,
        "internal_amount": internal_amount,
        "external_amount": external_amount,
        "difference": 0.0,
        "discrepancy_detected": False,
        "financial_impact": 0.0,
        "details": f"Amounts match perfectly: Internal ₹{internal_amount:,.2f} equals External ₹{external_amount:,.2f}. No discrepancy.",
    }
