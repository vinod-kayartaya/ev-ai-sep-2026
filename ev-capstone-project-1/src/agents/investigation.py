"""
Complaint Investigation Agent.
Responsible for:
- Understanding the natural language complaint
- Extracting customer and invoice IDs
- Retrieving customer information
- Retrieving internal billing information
- Calling external billing API
- Summarizing investigation results
"""

import re
from typing import Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from langfuse import observe
from src.config import get_llm
from src.tools.db_tools import get_customer, get_invoice, get_customer_invoices
from src.tools.billing_tools import get_external_billing
from src.state import AgentState


class ExtractionResult(BaseModel):
    customer_id: Optional[str] = Field(None, description="Identified customer ID, e.g. C1024")
    invoice_id: Optional[str] = Field(None, description="Identified invoice ID, e.g. INV10045")
    complaint_type: str = Field(..., description="Category: MISMATCH, DUPLICATE, OVERCHARGE, GENERAL_INQUIRY, INVALID")


def extract_entities_regex(text: str) -> Dict[str, Optional[str]]:
    """Fast regex extraction as fallback/primary assist."""
    cust_match = re.search(r"\b(C\d{4,6})\b", text, re.IGNORECASE)
    inv_match = re.search(r"\b(INV\d{4,6}(?:_DUP)?)\b", text, re.IGNORECASE)
    return {
        "customer_id": cust_match.group(1).upper() if cust_match else None,
        "invoice_id": inv_match.group(1).upper() if inv_match else None,
    }


@observe(name="Investigation_Agent")
def investigation_agent(state: AgentState) -> Dict[str, Any]:
    """
    Executes investigation: parses complaint, queries customer DB, invoice DB, and external billing.
    """
    complaint = state.get("complaint", "")
    llm = get_llm(temperature=0.0)

    # 1. Extract IDs using regex first, then LLM if needed
    regex_res = extract_entities_regex(complaint)
    cust_id = state.get("customer_id") or regex_res["customer_id"]
    inv_id = state.get("invoice_id") or regex_res["invoice_id"]

    if not cust_id or not inv_id:
        try:
            structured_llm = llm.with_structured_output(ExtractionResult)
            extraction_prompt = (
                f"Analyze this customer operations complaint and extract the Customer ID and Invoice ID if present:\n"
                f"Complaint: \"{complaint}\""
            )
            parsed: ExtractionResult = structured_llm.invoke([
                SystemMessage(content="You are an enterprise data extraction specialist. Extract IDs accurately."),
                HumanMessage(content=extraction_prompt)
            ])
            if not cust_id and parsed.customer_id:
                cust_id = parsed.customer_id.upper()
            if not inv_id and parsed.invoice_id:
                inv_id = parsed.invoice_id.upper()
        except Exception:
            pass

    # 2. Query Customer Information
    customer_data = None
    if cust_id:
        cust_lookup = get_customer.invoke({"customer_id": cust_id})
        if cust_lookup.get("status") == "SUCCESS":
            customer_data = cust_lookup.get("customer")

    # 3. If invoice_id is missing but we have customer_id, look up customer invoices
    invoice_data = None
    if not inv_id and cust_id:
        invoices_lookup = get_customer_invoices.invoke({"customer_id": cust_id})
        inv_list = invoices_lookup.get("invoices", [])
        if inv_list:
            inv_id = inv_list[0]["invoice_id"]
            invoice_data = inv_list[0]

    # 4. If invoice_id is known, look up internal invoice details
    if inv_id and not invoice_data:
        inv_lookup = get_invoice.invoke({"invoice_id": inv_id})
        if inv_lookup.get("status") == "SUCCESS":
            invoice_data = inv_lookup.get("invoice")
            if not cust_id and invoice_data:
                cust_id = invoice_data.get("customer_id")
                # Look up customer now
                cust_lookup = get_customer.invoke({"customer_id": cust_id})
                if cust_lookup.get("status") == "SUCCESS":
                    customer_data = cust_lookup.get("customer")

    # 5. Look up external billing record
    external_billing_data = None
    if inv_id:
        ext_lookup = get_external_billing.invoke({"invoice_id": inv_id})
        if ext_lookup.get("status") == "SUCCESS":
            external_billing_data = ext_lookup.get("billing_record")

    # 6. Formulate investigation summary
    findings = []
    if customer_data:
        findings.append(f"Customer {cust_id} ({customer_data.get('name')}, status: {customer_data.get('account_status')}) verified in internal database.")
    elif cust_id:
        findings.append(f"Customer {cust_id} NOT found in internal database.")
    else:
        findings.append("No customer ID identified in complaint.")

    if invoice_data:
        findings.append(f"Internal invoice {inv_id} found: Amount ₹{invoice_data.get('invoice_amount'):,.2f}, Status: {invoice_data.get('invoice_status')}, Date: {invoice_data.get('invoice_date')}.")
    elif inv_id:
        findings.append(f"Internal invoice {inv_id} NOT found in database.")
    else:
        findings.append("No invoice ID identified in complaint.")

    if external_billing_data:
        findings.append(f"External billing gateway confirms invoice {inv_id}: Amount ₹{external_billing_data.get('amount'):,.2f}, Status: {external_billing_data.get('status')}.")
    elif inv_id:
        findings.append(f"Invoice {inv_id} not found or unverified in external billing gateway.")

    summary = " ".join(findings)

    return {
        "customer_id": cust_id,
        "invoice_id": inv_id,
        "customer_data": customer_data,
        "invoice_data": invoice_data,
        "external_billing_data": external_billing_data,
        "investigation_summary": summary,
    }
