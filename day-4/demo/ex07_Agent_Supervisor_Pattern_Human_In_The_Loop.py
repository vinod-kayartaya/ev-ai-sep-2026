import os

from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command


# =========================================================
# State
# =========================================================

class OrderState(TypedDict):
    order_id: str
    request: str
    worker: str
    worker_result: str
    final_response: str

    # Number of times we asked the human for clarification
    clarification_count: int


# =========================================================
# LLM
# =========================================================

load_dotenv()

llm = ChatOpenAI(
    model=os.environ["MODEL_NAME"],
    temperature=0
)


# =========================================================
# Worker 1: Order Agent
# =========================================================

def order_worker(state: OrderState):

    print("\nOrder Worker")

    result = llm.invoke([
        HumanMessage(content=f"""
You are an Order Specialist.

Order ID: {state["order_id"]}
Customer request: {state["request"]}

Provide a short answer about the order.
""")
    ])

    return {
        "worker_result": result.content
    }


# =========================================================
# Worker 2: Payment Agent
# =========================================================

def payment_worker(state: OrderState):

    print("\nPayment Worker")

    result = llm.invoke([
        HumanMessage(content=f"""
You are a Payment Specialist.

Order ID: {state["order_id"]}
Customer request: {state["request"]}

Provide a short answer about the payment.
""")
    ])

    return {
        "worker_result": result.content
    }


# =========================================================
# Supervisor
# =========================================================

def supervisor(state: OrderState):

    print("\nSupervisor")

    result = llm.invoke([
        HumanMessage(content=f"""
You are the Supervisor of an order-processing system.

Customer request:
{state["request"]}

Determine which specialist should handle this request.

Rules:

1. If the request is clearly about an order, return exactly:
ORDER

2. If the request is clearly about payment, return exactly:
PAYMENT

3. If you cannot determine whether the request is about an
   order or payment, return exactly:
UNKNOWN

Do NOT guess.

Return ONLY one of:

ORDER
PAYMENT
UNKNOWN
""")
    ])

    decision = result.content.strip().upper()

    print("Supervisor selected:", decision)

    # -----------------------------------------------------
    # Clear decision
    # -----------------------------------------------------

    if decision == "ORDER":
        return {
            "worker": "order"
        }

    if decision == "PAYMENT":
        return {
            "worker": "payment"
        }

    # -----------------------------------------------------
    # LLM could not determine the issue
    # -----------------------------------------------------

    return {
        "worker": "unknown"
    }


# =========================================================
# Human-in-the-loop clarification
# =========================================================

def human_clarification(state: OrderState):

    count = state["clarification_count"]

    print(
        f"\nSupervisor could not determine the issue "
        f"(attempt {count + 1} of 5)."
    )

    # -----------------------------------------------------
    # Pause the graph and ask the human
    # -----------------------------------------------------

    additional_information = interrupt(
        {
            "message": (
                "I could not determine the type of issue. "
                "Please describe your problem again. "
                "Is it related to your order or payment?"
            )
        }
    )

    # -----------------------------------------------------
    # Resume the graph with the human's response
    # -----------------------------------------------------

    return {
        "request": additional_information,
        "clarification_count": count + 1
    }


# =========================================================
# Route Supervisor Decision
# =========================================================

def route_supervisor(state: OrderState):

    if state["worker"] == "order":
        return "order"

    if state["worker"] == "payment":
        return "payment"

    # LLM returned UNKNOWN
    return "clarification"


# =========================================================
# Route after clarification
# =========================================================

def route_after_clarification(state: OrderState):

    # -----------------------------------------------------
    # We have already used all 5 attempts
    # -----------------------------------------------------

    if state["clarification_count"] >= 4:
        return "exit"

    return "supervisor"


# =========================================================
# Exit after 5 failed attempts
# =========================================================

def clarification_failed(state: OrderState):

    print("\nSupervisor could not determine the issue.")

    return {
        "final_response": (
            "Sorry, I could not determine the type of issue "
            "from the information provided. "
            "Please contact customer support for further assistance."
        )
    }


# =========================================================
# Finalizer
# =========================================================

def finalize(state: OrderState):

    print("\nSupervisor - Finalizing response")

    result = llm.invoke([
        HumanMessage(content=f"""
You are the final response generator.

Customer request:
{state["request"]}

Specialist response:
{state["worker_result"]}

Create a concise final response for the customer.
Do not mention internal workers or supervisors.
""")
    ])

    return {
        "final_response": result.content
    }


# =========================================================
# Build Graph
# =========================================================

builder = StateGraph(OrderState)

builder.add_node("supervisor", supervisor)

builder.add_node(
    "human_clarification",
    human_clarification
)

builder.add_node(
    "clarification_failed",
    clarification_failed
)

builder.add_node(
    "order_worker",
    order_worker
)

builder.add_node(
    "payment_worker",
    payment_worker
)

builder.add_node(
    "finalize",
    finalize
)


# =========================================================
# Start
# =========================================================

builder.add_edge(
    START,
    "supervisor"
)


# =========================================================
# Supervisor routing
# =========================================================

builder.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "order": "order_worker",
        "payment": "payment_worker",
        "clarification": "human_clarification"
    }
)


# =========================================================
# Human clarification routing
# =========================================================

builder.add_conditional_edges(
    "human_clarification",
    route_after_clarification,
    {
        "supervisor": "supervisor",
        "exit": "clarification_failed"
    }
)


# =========================================================
# Workers
# =========================================================

builder.add_edge(
    "order_worker",
    "finalize"
)

builder.add_edge(
    "payment_worker",
    "finalize"
)


# =========================================================
# End paths
# =========================================================

builder.add_edge(
    "finalize",
    END
)

builder.add_edge(
    "clarification_failed",
    END
)


# =========================================================
# Compile with checkpointing
# =========================================================

memory = MemorySaver()

graph = builder.compile(
    checkpointer=memory
)

# =========================================================
# Run
# =========================================================

config = {
    "configurable": {
        "thread_id": "customer-1001"
    }
}


result = graph.invoke(
    {
        "order_id": "ORD1001",
        "request": input("\n>> "),
        "worker": "",
        "worker_result": "",
        "final_response": "",
        "clarification_count": 0
    },
    config
)


# =========================================================
# Human-in-the-loop loop
# =========================================================

while "__interrupt__" in result:

    interrupt_data = result["__interrupt__"][0]

    print("\n" + interrupt_data.value["message"])

    user_input = input("\n>> ")

    result = graph.invoke(
        Command(resume=user_input),
        config
    )


# =========================================================
# Final result
# =========================================================

print("\nFinal response:")
print(result["final_response"])