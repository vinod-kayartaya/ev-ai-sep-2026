from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
# from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command


class OrderState(TypedDict):
    order_id: str
    amount: float
    status: str
    approved: bool


def create_order(state: OrderState):
    print("Creating order...")

    return {
        "status": "PENDING_APPROVAL"
    }


def request_approval(state: OrderState):

    # Execution stops here.
    # The value is returned to the application/UI.
    decision = interrupt({
        "message": "Human approval required",
        "order_id": state["order_id"],
        "amount": state["amount"]
    })

    return {
        "approved": decision
    }


def process_order(state: OrderState):

    if state["approved"]:
        print("Processing order...")
        return {"status": "PROCESSED"}

    print("Order rejected.")
    return {"status": "REJECTED"}


# ---------------------------------------------------------
# Build graph
# ---------------------------------------------------------

builder = StateGraph(OrderState)

builder.add_node("create_order", create_order)
builder.add_node("request_approval", request_approval)
builder.add_node("process_order", process_order)

builder.add_edge(START, "create_order")
builder.add_edge("create_order", "request_approval")
builder.add_edge("request_approval", "process_order")
builder.add_edge("process_order", END)


# ---------------------------------------------------------
# Persistent checkpointer
# ---------------------------------------------------------


with SqliteSaver.from_conn_string("orders.db") as checkpointer:

    graph = builder.compile(
        checkpointer=checkpointer
    )

    # graph.get_graph().draw_png(output_file_path="ex05.png")
    # exit(0)

    config = {
        "configurable": {
            "thread_id": "ORDER-1001"
        }
    }

    # -----------------------------------------------------
    # Start the graph
    # -----------------------------------------------------

    result = graph.invoke(
        {
            "order_id": "ORD1001",
            "amount": 75000,
            "status": "NEW",
            "approved": False
        },
        config
    )
    

    # -----------------------------------------------------
    # Graph has paused at interrupt()
    # -----------------------------------------------------

    print("\nGraph paused.")

    print(
        "Approval request:",
        result["__interrupt__"][0].value
    )

    # -----------------------------------------------------
    # HUMAN INTERACTION
    # -----------------------------------------------------

    answer = input(
        "\nApprove this order? (yes/no): "
    )

    approved = answer.lower() == "yes"

    # -----------------------------------------------------
    # Resume graph with human's decision
    # -----------------------------------------------------

    result = graph.invoke(
        Command(resume=approved),
        config
    )

    print("\nFinal result:")
    print(result)
