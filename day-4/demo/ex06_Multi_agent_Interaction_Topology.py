import os

from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from langgraph.graph import StateGraph, START, END


# ---------------------------------------------------------
# State
# ---------------------------------------------------------

class OrderState(TypedDict):
    order_id: str
    message: str
    response: str
    next_agent: str


# ---------------------------------------------------------
# LLM
# ---------------------------------------------------------

load_dotenv()

llm = ChatOpenAI(
    model=os.environ["MODEL_NAME"],
    temperature=0
)


# ---------------------------------------------------------
# Order Agent
# ---------------------------------------------------------

def order_agent(state: OrderState):

    prompt = f"""
You are an Order Agent.

Customer request:
{state["message"]}

Order ID:
{state["order_id"]}

Decide what should happen next.

If this is a payment-related issue, respond exactly:
HANDOFF:PAYMENT

If this is a product quality related issue, respond exactly:
HANDOFF:QUALITY


Otherwise, respond with:
HANDLE:ORDER
"""

    result = llm.invoke(
        [HumanMessage(content=prompt)]
    )

    decision = result.content.strip()

    print("\nOrder Agent:")
    print(decision)

    if decision == "HANDOFF:PAYMENT":
        return {
            "next_agent": "payment"
        }
    if decision == "HANDOFF:QUALITY":
        return {
            "next_agent": "quality"
        }

    return {
        "next_agent": "order",
        "response": "Order Agent handled the request."
    }


# ---------------------------------------------------------
# Payment Agent
# ---------------------------------------------------------

def payment_agent(state: OrderState):

    print("\nPayment Agent:")
    print("Payment Agent received the handoff.")

    return {
        "response": (
            f"Payment Agent is checking payment "
            f"for order {state['order_id']}."
        )
    }

# ---------------------------------------------------------
# Quality Agent
# ---------------------------------------------------------

def quality_agent(state: OrderState):

    print("\nQuality Agent:")
    print("Quality Agent received the handoff.")

    return {
        "response": (
            f"Quality Agent is checking quality "
            f"for order {state['order_id']}."
        )
    }


# ---------------------------------------------------------
# Routing after Order Agent
# ---------------------------------------------------------

def route_from_order(state: OrderState):
    return state["next_agent"]


# ---------------------------------------------------------
# Build Graph
# ---------------------------------------------------------

builder = StateGraph(OrderState)

builder.add_node(
    "order_agent",
    order_agent
)

builder.add_node(
    "payment_agent",
    payment_agent
)

builder.add_node(
    "quality_agent",
    quality_agent
)

builder.add_edge(
    START,
    "order_agent"
)

builder.add_conditional_edges(
    "order_agent",
    route_from_order,
    {
        "order": END,
        "payment": "payment_agent",
        "quality": "quality_agent"
    }
)

builder.add_edge(
    "payment_agent",
    END
)

graph = builder.compile()


# ---------------------------------------------------------
# Run
# ---------------------------------------------------------

result = graph.invoke({
    "order_id": "ORD1001",
    "message": "The item was damaged when I received",
    "response": "",
    "next_agent": ""
})

print("\nFinal response:")
print(result["response"])