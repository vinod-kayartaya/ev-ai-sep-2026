#!/usr/bin/env python3
"""
Automated Evaluation Suite for Enterprise Operations Assistant.
Tests 5 representative scenarios as specified in Capstone_Project.md Section 12:
1. Billing amount mismatch
2. Duplicate charge
3. Correct billing
4. Financial adjustment with Human-in-the-Loop approval
5. Invalid customer / invoice handling

Measures accuracy across 5 dimensions and captures actual execution latency.
Outputs evaluation report in Markdown and JSON formats.
"""

import time
import json
import os
from typing import Dict, Any, List
from tabulate import tabulate
from run_assistant import process_complaint
from setup_db import init_db
from src.config import configure_observability, LANGFUSE_HOST

EVAL_SCENARIOS = [
    {
        "id": "scenario_1",
        "name": "Billing amount mismatch",
        "complaint": "Customer C1024 has complained that they were charged ₹12,500 for invoice INV10045, but the amount shown by the billing system is ₹10,000. Investigate the discrepancy and recommend an appropriate resolution.",
        "expected_customer": "C1024",
        "expected_invoice": "INV10045",
        "expected_discrepancy": 2500.0,
        "requires_adjustment": True,
        "auto_approve": True,
    },
    {
        "id": "scenario_2",
        "name": "Duplicate charge",
        "complaint": "Customer C1025 reports being charged ₹3,000 twice on invoice INV10046. Please verify duplicate billing and recommend resolution.",
        "expected_customer": "C1025",
        "expected_invoice": "INV10046",
        "expected_discrepancy": 3000.0,
        "requires_adjustment": True,
        "auto_approve": True,
    },
    {
        "id": "scenario_3",
        "name": "Correct billing",
        "complaint": "Customer C1026 inquired about invoice INV10047 for ₹7,500 claiming an overcharge. Please verify against external billing records.",
        "expected_customer": "C1026",
        "expected_invoice": "INV10047",
        "expected_discrepancy": 0.0,
        "requires_adjustment": False,
        "auto_approve": None,
    },
    {
        "id": "scenario_4",
        "name": "Financial adjustment (HITL)",
        "complaint": "Customer C1027 reports invoice INV10048 was charged at ₹18,000 instead of the discounted ₹14,500 rate. Reconcile and apply appropriate adjustment.",
        "expected_customer": "C1027",
        "expected_invoice": "INV10048",
        "expected_discrepancy": 3500.0,
        "requires_adjustment": True,
        "auto_approve": True,
    },
    {
        "id": "scenario_5",
        "name": "Invalid customer/invoice",
        "complaint": "Customer C9999 inquired about invoice INV99999 for ₹50,000 which cannot be recognized.",
        "expected_customer": "C9999",
        "expected_invoice": "INV99999",
        "expected_discrepancy": 0.0,
        "requires_adjustment": False,
        "auto_approve": None,
    },
]


def run_evaluation() -> Dict[str, Any]:
    print("=" * 80)
    print("STARTING AUTOMATED EVALUATION SUITE")
    print("=" * 80)

    is_online = configure_observability()
    if is_online:
        print(f"[Observability] Connected to Langfuse at {LANGFUSE_HOST}.")
    else:
        print(f"[Observability] Local Langfuse at {LANGFUSE_HOST} is offline. Console retry logs silenced.")

    # Re-initialize clean test database
    init_db()

    results: List[Dict[str, Any]] = []

    for i, sc in enumerate(EVAL_SCENARIOS, 1):
        print(f"\n[{i}/5] Running: {sc['name']}...")
        start_time = time.perf_counter()

        try:
            state_result = process_complaint(
                complaint_text=sc["complaint"],
                thread_id=f"eval_{sc['id']}_{int(time.time())}",
                auto_approve=sc["auto_approve"],
                verbose=False,
            )
            elapsed_time = round(time.perf_counter() - start_time, 2)

            # Evaluate Criteria
            criteria = {}

            # 1. Customer & Invoice identification
            cid = state_result.get("customer_id")
            iid = state_result.get("invoice_id")
            criteria["entity_identification"] = (cid == sc["expected_customer"] and iid == sc["expected_invoice"])

            # 2. Information retrieval
            if sc["id"] == "scenario_5":
                # For invalid IDs, info retrieval passes if recognized as absent
                criteria["information_retrieval"] = (state_result.get("customer_data") is None)
            else:
                criteria["information_retrieval"] = (
                    state_result.get("customer_data") is not None and
                    state_result.get("invoice_data") is not None
                )

            # 3. Discrepancy & Reconciliation accuracy
            rec = state_result.get("reconciliation_result") or {}
            if sc["id"] == "scenario_5":
                criteria["reconciliation_accuracy"] = True
            elif sc["requires_adjustment"]:
                criteria["reconciliation_accuracy"] = (
                    rec.get("discrepancy_detected") is True and
                    abs(rec.get("financial_impact", 0.0) - sc["expected_discrepancy"]) < 1.0
                )
            else:
                criteria["reconciliation_accuracy"] = (
                    rec.get("discrepancy_detected") is False
                )

            # 4. Human-in-the-Loop handling
            if sc["requires_adjustment"]:
                criteria["hitl_handling"] = (state_result.get("approval_status") == "APPROVED")
            else:
                criteria["hitl_handling"] = (state_result.get("approval_status") == "NOT_REQUIRED")

            # 5. Final resolution generated
            criteria["resolution_generated"] = bool(
                state_result.get("final_response") and
                "Complaint Investigation Completed" in state_result.get("final_response", "")
            )

            passed_checks = sum(1 for v in criteria.values() if v)
            total_checks = len(criteria)
            accuracy_pct = round((passed_checks / total_checks) * 100, 1)
            scenario_pass = (accuracy_pct == 100.0)

            results.append({
                "scenario": sc["name"],
                "result": "Pass" if scenario_pass else "Fail",
                "accuracy": f"{accuracy_pct:.0f}%",
                "accuracy_num": accuracy_pct,
                "latency": f"{elapsed_time:.1f} sec",
                "latency_sec": elapsed_time,
                "criteria": criteria,
                "final_summary": state_result.get("final_response"),
            })

            print(f" -> Result: {'PASS' if scenario_pass else 'FAIL'} | Accuracy: {accuracy_pct}% | Latency: {elapsed_time}s")

        except Exception as e:
            elapsed_time = round(time.perf_counter() - start_time, 2)
            results.append({
                "scenario": sc["name"],
                "result": "Error",
                "accuracy": "0%",
                "accuracy_num": 0.0,
                "latency": f"{elapsed_time:.1f} sec",
                "latency_sec": elapsed_time,
                "error": str(e),
            })
            print(f" -> ERROR: {e}")

    # Generate Summary Table
    table_data = [
        [r["scenario"], r["result"], r["accuracy"], r["latency"]]
        for r in results
    ]

    headers = ["Scenario", "Result", "Accuracy", "Latency"]
    formatted_table = tabulate(table_data, headers=headers, tablefmt="github")

    avg_latency = round(sum(r["latency_sec"] for r in results) / len(results), 2)
    overall_accuracy = round(sum(r["accuracy_num"] for r in results) / len(results), 1)

    print("\n" + "=" * 80)
    print("EVALUATION RESULTS SUMMARY")
    print("=" * 80)
    print(formatted_table)
    print(f"\nOverall Accuracy: {overall_accuracy}% | Average Latency: {avg_latency} sec\n")

    # Save JSON results
    eval_output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "overall_accuracy": f"{overall_accuracy}%",
        "average_latency": f"{avg_latency} sec",
        "scenarios": results,
    }

    with open("evaluation_results.json", "w") as f:
        json.dump(eval_output, f, indent=2)

    # Save Markdown report
    report_md = f"""# Enterprise Operations Assistant - Evaluation Report

Generated: {eval_output['timestamp']}

## Executive Summary

The evaluation suite executes 5 representative business scenarios testing the core operational capabilities:
- Dynamic entity extraction & database lookup
- Third-party REST billing reconciliation
- Duplicate charge detection
- Correct billing verification
- Human-in-the-Loop financial approval
- Graceful error handling for invalid entities

| Metric | Result |
| :--- | :--- |
| **Overall Accuracy** | **{overall_accuracy}%** |
| **Average Latency** | **{avg_latency} sec** |
| **Total Test Scenarios** | **5** |
| **Passed Scenarios** | **{sum(1 for r in results if r['result'] == 'Pass')} / 5** |

---

## Scenario Performance

{formatted_table}

---

## Detailed Scenario Breakdown

"""
    for r in results:
        report_md += f"### {r['scenario']}\n\n"
        report_md += f"- **Result**: `{r['result']}`\n"
        report_md += f"- **Accuracy**: {r['accuracy']}\n"
        report_md += f"- **Execution Latency**: {r['latency']}\n"
        if "criteria" in r:
            report_md += "- **Criteria Checks**:\n"
            for crit, passed in r["criteria"].items():
                icon = "✅" if passed else "❌"
                report_md += f"  - {icon} `{crit}`\n"
        if r.get("final_summary"):
            report_md += f"\n**Final Assistant Response**:\n```text\n{r['final_summary']}\n```\n\n"
        report_md += "---\n\n"

    with open("evaluation_report.md", "w") as f:
        f.write(report_md)

    print("Saved evaluation report to 'evaluation_report.md' and raw data to 'evaluation_results.json'.")
    return eval_output


if __name__ == "__main__":
    run_evaluation()
