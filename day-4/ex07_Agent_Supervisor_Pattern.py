import os

from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from langgraph.graph import StateGraph, START, END


# =========================================================
# State
# =========================================================

class OrderState(TypedDict):
    order_id: str
    request: str
    worker: str
    worker_result: str
    final_response: str


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

Choose the appropriate worker.

Return ONLY one of:

ORDER
PAYMENT
""")
    ])

    decision = result.content.strip().upper()

    print("Supervisor selected:", decision)

    if "PAYMENT" in decision:
        return {
            "worker": "payment"
        }

    return {
        "worker": "order"
    }


# =========================================================
# Route Supervisor Decision
# =========================================================

def route_worker(state: OrderState):

    return state["worker"]


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
builder.add_node("order_worker", order_worker)
builder.add_node("payment_worker", payment_worker)
builder.add_node("finalize", finalize)

builder.add_edge(
    START,
    "supervisor"
)

builder.add_conditional_edges(
    "supervisor",
    route_worker,
    {
        "order": "order_worker",
        "payment": "payment_worker"
    }
)

builder.add_edge(
    "order_worker",
    "finalize"
)

builder.add_edge(
    "payment_worker",
    "finalize"
)

builder.add_edge(
    "finalize",
    END
)

graph = builder.compile()


# =========================================================
# Run
# =========================================================

result = graph.invoke({
    "order_id": "ORD1001",
    "request": "I was charged twice for my order.",
    "worker": "",
    "worker_result": "",
    "final_response": ""
})

print("\nFinal response:")
print(result["final_response"])