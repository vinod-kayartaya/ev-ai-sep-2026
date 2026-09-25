"""
Audit logging tool for recording completed complaint resolutions in the database.
"""

from typing import Dict, Any, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langfuse import observe
from src.db import insert_resolution_log


class LogResolutionInput(BaseModel):
    customer_id: str = Field(description="The customer ID, e.g. C1024")
    complaint: str = Field(description="Original complaint description")
    resolution: str = Field(description="Final resolution or recommended action")
    invoice_id: Optional[str] = Field(default=None, description="Related invoice ID, if any")
    investigation_result: Optional[str] = Field(default="", description="Summary of investigation findings")
    reconciliation_result: Optional[str] = Field(default="", description="Summary of reconciliation findings")
    financial_adjustment_amount: Optional[float] = Field(default=0.0, description="Amount of financial adjustment")
    approval_decision: Optional[str] = Field(default="NOT_REQUIRED", description="Supervisor approval decision: APPROVED, REJECTED, or NOT_REQUIRED")
    final_status: Optional[str] = Field(default="Completed", description="Final resolution status")


@tool("log_resolution", args_schema=LogResolutionInput)
@observe(name="log_resolution")
def log_resolution(
    customer_id: str,
    complaint: str,
    resolution: str,
    invoice_id: Optional[str] = None,
    investigation_result: Optional[str] = "",
    reconciliation_result: Optional[str] = "",
    financial_adjustment_amount: Optional[float] = 0.0,
    approval_decision: Optional[str] = "NOT_REQUIRED",
    final_status: Optional[str] = "Completed",
) -> Dict[str, Any]:
    """Securely log the final investigation and resolution outcome to the database audit table."""
    log_id = insert_resolution_log(
        customer_id=customer_id,
        complaint=complaint,
        invoice_id=invoice_id,
        investigation_result=investigation_result or "",
        reconciliation_result=reconciliation_result or "",
        recommended_resolution=resolution,
        financial_adjustment_amount=financial_adjustment_amount or 0.0,
        approval_decision=approval_decision,
        final_status=final_status or "Completed",
    )
    return {
        "status": "SUCCESS",
        "log_id": log_id,
        "message": f"Resolution successfully recorded in audit log with ID #{log_id}.",
    }
