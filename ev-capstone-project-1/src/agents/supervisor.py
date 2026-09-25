"""
Supervisor Agent.
Responsible for:
- Coordinating specialized agents (Investigation, Reconciliation, Resolution)
- Determining dynamic routing decisions
- Checking whether financial adjustment requires human approval
- Deciding when the workflow is completed
"""

from typing import Dict, Any, Literal
from langfuse import observe
from src.state import AgentState


@observe(name="Supervisor_Agent")
def supervisor_agent(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates current workflow state and decides the next step.
    """
    # 1. Has investigation been performed?
    if not state.get("investigation_summary"):
        return {"next_step": "investigation_agent"}

    # 2. Has reconciliation been performed?
    if not state.get("reconciliation_result"):
        return {"next_step": "reconciliation_agent"}

    # 3. Has resolution recommendation been produced?
    if not state.get("recommended_resolution"):
        return {"next_step": "resolution_agent"}

    # 4. Does it require financial adjustment and is human approval pending?
    if state.get("requires_financial_adjustment") and state.get("approval_status") == "PENDING":
        return {"next_step": "human_approval"}

    # 5. Has final action and audit logging been performed?
    if not state.get("final_response"):
        return {"next_step": "execute_and_log"}

    # 6. Everything completed
    return {"next_step": "END"}


def route_supervisor(state: AgentState) -> str:
    """
    Conditional edge router based on supervisor's next_step.
    """
    next_step = state.get("next_step")
    if next_step in ["investigation_agent", "reconciliation_agent", "resolution_agent", "human_approval", "execute_and_log"]:
        return next_step
    return "END"
