"""
External billing tool for interacting with the third-party billing REST API.
"""

from typing import Dict, Any
import requests
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langfuse import observe
from src.config import MOCK_API_BASE_URL
from mock_service.mock_billing_api import query_mock_billing_direct


class GetExternalBillingInput(BaseModel):
    invoice_id: str = Field(description="The invoice ID to query in the external billing system, e.g. INV10045")


@tool("get_external_billing", args_schema=GetExternalBillingInput)
@observe(name="get_external_billing")
def get_external_billing(invoice_id: str) -> Dict[str, Any]:
    """Retrieve verified billing record from the external third-party billing gateway API."""
    clean_id = invoice_id.strip().upper()
    url = f"{MOCK_API_BASE_URL}/billing/{clean_id}"

    try:
        response = requests.get(url, timeout=3.0)
        if response.status_code == 200:
            return {
                "status": "SUCCESS",
                "source": "EXTERNAL_REST_API",
                "billing_record": response.json(),
            }
        elif response.status_code == 404:
            return {
                "status": "NOT_FOUND",
                "source": "EXTERNAL_REST_API",
                "message": f"Invoice '{clean_id}' was not found in the external billing gateway.",
            }
    except Exception:
        # Fallback to direct mock query if REST API server is not running on port 8000
        pass

    direct_res = query_mock_billing_direct(clean_id)
    if direct_res:
        return {
            "status": "SUCCESS",
            "source": "MOCK_GATEWAY_DIRECT",
            "billing_record": direct_res,
        }
    return {
        "status": "NOT_FOUND",
        "source": "MOCK_GATEWAY_DIRECT",
        "message": f"Invoice '{clean_id}' not found in external billing system.",
    }
