"""
Database tools for customer, invoice, and adjustment operations.
"""

from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langfuse import observe
from src.db import (
    fetch_customer,
    fetch_invoice,
    fetch_customer_invoices,
    insert_financial_adjustment,
    update_adjustment,
)


class GetCustomerInput(BaseModel):
    customer_id: str = Field(description="The unique identifier of the customer, e.g. C1024")


@tool("get_customer", args_schema=GetCustomerInput)
@observe(name="get_customer")
def get_customer(customer_id: str) -> Dict[str, Any]:
    """Retrieve customer details such as name, email, and account status from the database."""
    res = fetch_customer(customer_id)
    if res:
        return {"status": "SUCCESS", "customer": res}
    return {"status": "NOT_FOUND", "message": f"Customer '{customer_id}' not found in database."}


class GetInvoiceInput(BaseModel):
    invoice_id: str = Field(description="The unique identifier of the invoice, e.g. INV10045")


@tool("get_invoice", args_schema=GetInvoiceInput)
@observe(name="get_invoice")
def get_invoice(invoice_id: str) -> Dict[str, Any]:
    """Retrieve invoice details including customer_id, amount, status, and date from the database."""
    res = fetch_invoice(invoice_id)
    if res:
        return {"status": "SUCCESS", "invoice": res}
    return {"status": "NOT_FOUND", "message": f"Invoice '{invoice_id}' not found in database."}


class GetCustomerInvoicesInput(BaseModel):
    customer_id: str = Field(description="The unique identifier of the customer, e.g. C1024")


@tool("get_customer_invoices", args_schema=GetCustomerInvoicesInput)
@observe(name="get_customer_invoices")
def get_customer_invoices(customer_id: str) -> Dict[str, Any]:
    """Retrieve all invoices associated with a specific customer."""
    invoices = fetch_customer_invoices(customer_id)
    return {
        "status": "SUCCESS",
        "customer_id": customer_id,
        "count": len(invoices),
        "invoices": invoices,
    }


class CreateFinancialAdjustmentInput(BaseModel):
    customer_id: str = Field(description="Customer ID receiving the adjustment, e.g. C1024")
    invoice_id: str = Field(description="Invoice ID the adjustment applies to, e.g. INV10045")
    amount: float = Field(description="Adjustment amount in INR (positive value)")
    reason: str = Field(description="Reason for financial adjustment, e.g. 'Billing discrepancy'")


@tool("create_financial_adjustment", args_schema=CreateFinancialAdjustmentInput)
@observe(name="create_financial_adjustment")
def create_financial_adjustment(
    customer_id: str,
    invoice_id: str,
    amount: float,
    reason: str,
) -> Dict[str, Any]:
    """Create a pending financial adjustment record in the database for supervisor approval."""
    adj_id = insert_financial_adjustment(
        customer_id=customer_id,
        invoice_id=invoice_id,
        amount=amount,
        reason=reason,
        status="Pending",
    )
    return {
        "status": "SUCCESS",
        "adjustment_id": adj_id,
        "customer_id": customer_id,
        "invoice_id": invoice_id,
        "amount": amount,
        "adjustment_status": "Pending",
        "reason": reason,
        "message": f"Financial adjustment {adj_id} for ₹{amount:,.2f} created with status 'Pending'.",
    }


class UpdateAdjustmentStatusInput(BaseModel):
    adjustment_id: str = Field(description="The unique identifier of the adjustment, e.g. ADJ1001")
    status: str = Field(description="New status: 'Approved' or 'Rejected'")


@tool("update_adjustment_status", args_schema=UpdateAdjustmentStatusInput)
@observe(name="update_adjustment_status")
def update_adjustment_status(adjustment_id: str, status: str) -> Dict[str, Any]:
    """Update the status of an existing financial adjustment (e.g. to Approved or Rejected)."""
    success = update_adjustment(adjustment_id, status)
    if success:
        return {
            "status": "SUCCESS",
            "adjustment_id": adjustment_id,
            "new_status": status,
            "message": f"Adjustment {adjustment_id} updated to '{status}'.",
        }
    return {
        "status": "NOT_FOUND",
        "message": f"Adjustment {adjustment_id} could not be found or updated.",
    }
