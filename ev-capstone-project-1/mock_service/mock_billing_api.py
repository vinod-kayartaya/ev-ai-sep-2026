"""
Mock External Billing REST API.
Represents the third-party billing system described in Capstone_Project.md Section 5.
Can be run as a standalone FastAPI server or called in-process as fallback.
"""

from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
import uvicorn

app = FastAPI(
    title="Mock Third-Party Billing API",
    description="Simulates an external billing gateway for invoice verification",
    version="1.0.0",
)

# External billing records
EXTERNAL_BILLING_DATABASE: Dict[str, Dict[str, Any]] = {
    "INV10045": {
        "invoice_id": "INV10045",
        "customer_id": "C1024",
        "amount": 10000.0,
        "currency": "INR",
        "status": "PAID",
        "billing_date": "2026-09-20",
        "notes": "Verified third-party transaction of ₹10,000"
    },
    "INV10046": {
        "invoice_id": "INV10046",
        "customer_id": "C1025",
        "amount": 3000.0,
        "currency": "INR",
        "status": "PAID",
        "billing_date": "2026-09-21",
        "notes": "Single charge of ₹3,000 processed for subscription cycle"
    },
    "INV10047": {
        "invoice_id": "INV10047",
        "customer_id": "C1026",
        "amount": 7500.0,
        "currency": "INR",
        "status": "PAID",
        "billing_date": "2026-09-22",
        "notes": "Exact matching charge"
    },
    "INV10048": {
        "invoice_id": "INV10048",
        "customer_id": "C1027",
        "amount": 14500.0,
        "currency": "INR",
        "status": "PAID",
        "billing_date": "2026-09-23",
        "notes": "Discounted rate reflected at billing gateway"
    },
    "INV10049": {
        "invoice_id": "INV10049",
        "customer_id": "C1028",
        "amount": 5000.0,
        "currency": "INR",
        "status": "PAID",
        "billing_date": "2026-09-24",
        "notes": "Standard plan"
    },
}


@app.get("/health")
def health():
    return {"status": "ok", "service": "external-billing-api"}


@app.get("/billing/{invoice_id}")
def get_billing(invoice_id: str):
    """Retrieve billing record for given invoice_id from the third-party system."""
    clean_id = invoice_id.strip().upper()
    if clean_id in EXTERNAL_BILLING_DATABASE:
        return EXTERNAL_BILLING_DATABASE[clean_id]
    raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found in external billing system")


def query_mock_billing_direct(invoice_id: str) -> Optional[Dict[str, Any]]:
    """In-process direct fallback query without HTTP."""
    clean_id = invoice_id.strip().upper()
    return EXTERNAL_BILLING_DATABASE.get(clean_id)


def start_server(host: str = "127.0.0.1", port: int = 8000):
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    start_server()
