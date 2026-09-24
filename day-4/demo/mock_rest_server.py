from flask import Flask, jsonify

app = Flask(__name__)

invoices = {
    "INV10045": {
        "invoice_id": "INV10045",
        "customer_id": "C1024",
        "amount": 10000,
        "currency": "INR",
        "status": "PAID",
        "billing_date": "2026-09-20"
    },
    "INV10046": {
        "invoice_id": "INV10046",
        "customer_id": "QWE123",
        "amount": 41119,
        "currency": "INR",
        "status": "PAID",
        "billing_date": "2026-09-20"
    },
    "INV10067": {
            "invoice_id": "INV10067",
            "customer_id": "ASD123",
            "amount": 49888,
            "currency": "INR",
            "status": "PAID",
            "billing_date": "2026-09-20"
        }
    
}


@app.route("/billing/<string:invoice_id>")
def get_billing(invoice_id: str):

    err = {
        "success": False,
        "message": f"No data found for id {invoice_id}"
    }
    return jsonify(invoices.get(invoice_id, err))

app.run(host="0.0.0.0", port=5000, debug=True)