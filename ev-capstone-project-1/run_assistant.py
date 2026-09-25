#!/usr/bin/env python3
"""
Enterprise Operations Assistant - Interactive & CLI Runner
Executes the LangGraph multi-agent workflow with Human-in-the-Loop supervisor approval
and Langfuse observability tracing.
"""

import sys
import uuid
from typing import Optional
from langfuse import observe
from langgraph.types import Command
from src.workflow import build_operations_workflow
from src.config import get_langfuse_callback, LANGFUSE_HOST, configure_observability, is_langfuse_reachable


@observe(name="Enterprise_Operations_Assistant")
def process_complaint(
    complaint_text: str,
    thread_id: Optional[str] = None,
    auto_approve: Optional[bool] = None,
    verbose: bool = True,
):
    """
    Processes a natural language complaint through the LangGraph workflow.
    Handles supervisor human-in-the-loop approval when required.
    """
    if not thread_id:
        thread_id = f"session_{uuid.uuid4().hex[:8]}"

    langfuse_online = configure_observability()

    if verbose:
        print("\n" + "=" * 70)
        print("ENTERPRISE OPERATIONS ASSISTANT")
        print("=" * 70)
        print(f"Complaint: \"{complaint_text}\"")
        print(f"Session Thread ID: {thread_id}")
        if langfuse_online:
            print(f"[Observability] Connected to Langfuse at {LANGFUSE_HOST}.")
        else:
            print(f"[Observability] Local Langfuse at {LANGFUSE_HOST} is offline. Console retry logs silenced.")

    # Initialize Langfuse CallbackHandler
    langfuse_handler = get_langfuse_callback(
        trace_name="Complaint_Resolution_Workflow",
        session_id=thread_id,
        tags=["enterprise-operations", "cli-execution"],
    )

    callbacks = [langfuse_handler] if langfuse_handler else []
    config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": callbacks,
    }

    app = build_operations_workflow()

    initial_state = {
        "messages": [],
        "complaint": complaint_text,
        "customer_id": None,
        "invoice_id": None,
        "customer_data": None,
        "invoice_data": None,
        "external_billing_data": None,
        "investigation_summary": None,
        "reconciliation_result": None,
        "recommended_resolution": None,
        "requires_financial_adjustment": False,
        "financial_adjustment_amount": 0.0,
        "adjustment_reason": None,
        "adjustment_id": None,
        "approval_status": "NOT_REQUIRED",
        "next_step": None,
        "final_response": None,
        "error": None,
    }

    if verbose:
        print("\n[Workflow] Starting Multi-Agent Orchestration...")

    # Execute workflow until completion or interrupt
    result = app.invoke(initial_state, config=config)

    # Check if workflow was interrupted for Human-in-the-Loop approval
    snapshot = app.get_state(config)
    if snapshot.tasks and any(task.interrupts for task in snapshot.tasks):
        interrupt_info = snapshot.tasks[0].interrupts[0].value
        if verbose:
            print("\n" + "=" * 70)
            print("HUMAN-IN-THE-LOOP: SUPERVISOR APPROVAL REQUIRED")
            print("=" * 70)
            print(f"Customer       : {interrupt_info.get('customer_id')}")
            print(f"Invoice        : {interrupt_info.get('invoice_id')}")
            int_amt = interrupt_info.get('internal_amount')
            ext_amt = interrupt_info.get('external_amount')
            if int_amt is not None:
                print(f"Internal Amount: ₹{int_amt:,.2f}")
            if ext_amt is not None:
                print(f"External Amount: ₹{ext_amt:,.2f}")
            print(f"Discrepancy    : ₹{interrupt_info.get('discrepancy', 0.0):,.2f}")
            print(f"\nFinding:\n{interrupt_info.get('finding')}")
            print(f"\nRecommended Action:\n{interrupt_info.get('recommended_action')}")
            print(f"\nReason:\n{interrupt_info.get('reason')}")
            print("=" * 70)

        # Determine supervisor decision
        if auto_approve is True:
            decision = "APPROVE"
            if verbose:
                print("[Supervisor Action] Auto-approved via execution flag.")
        elif auto_approve is False:
            decision = "REJECT"
            if verbose:
                print("[Supervisor Action] Auto-rejected via execution flag.")
        else:
            # Interactive prompt
            prompt_input = input("\nEnter decision [APPROVE / REJECT] (default: APPROVE): ").strip().upper()
            decision = "REJECT" if "REJ" in prompt_input else "APPROVE"
            if verbose:
                print(f"[Supervisor Action] Decision recorded: {decision}")

        if verbose:
            print("\n[Workflow] Resuming execution with supervisor decision...")

        # Resume workflow with human decision
        result = app.invoke(Command(resume=decision), config=config)

    if verbose:
        print("\n" + "=" * 70)
        print("FINAL OPERATIONAL SUMMARY")
        print("=" * 70)
        print(result.get("final_response", "No response generated."))
        print("=" * 70)

    # Flush Langfuse traces if active and server reachable
    if langfuse_online and langfuse_handler:
        try:
            langfuse_handler.flush()
            if verbose:
                print(f"\n[Langfuse] Traces recorded and flushed to {LANGFUSE_HOST}")
        except Exception:
            pass

    return result


def main():
    print("=" * 70)
    print("ENTERPRISE OPERATIONS ASSISTANT")
    print("Interactive Operations Console")
    print("Type 'exit' or 'quit' to end (or press Ctrl+C).")
    print("=" * 70)

    while True:
        try:
            complaint = input("\nEnter customer complaint:\n> ").strip()
            if complaint.lower() in ["exit", "quit"]:
                print("\nExiting Enterprise Operations Assistant. Goodbye!")
                break
            if not complaint:
                continue

            process_complaint(complaint, verbose=True)

        except (KeyboardInterrupt, EOFError):
            print("\n\nSession terminated by user (Ctrl+C). Goodbye!")
            break


if __name__ == "__main__":
    main()
