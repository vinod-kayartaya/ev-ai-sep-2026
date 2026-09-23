import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import create_agent


# =========================================================
# Primary Order System
# =========================================================

@tool
def get_order_from_primary(order_id: str):
    """Get an order from the primary order system."""

    # Simulate a system failure
    raise Exception("Primary order system is unavailable")


# =========================================================
# Backup Order System
# =========================================================

@tool
def get_order_from_backup(order_id: str):
    """Get an order from the backup order system."""

    orders = {
        "ORD1001": {
            "status": "SHIPPED",
            "customer": "John"
        }
    }

    return orders.get(order_id, "Order not found")


# =========================================================
# Safe wrapper with Error Recovery + Fallback
# =========================================================

@tool
def get_order(order_id: str):
    """
    Get order details.

    Try the primary system first.
    If it fails, use the backup system.
    """

    try:
        # ---------------------------------------------
        # Primary system
        # ---------------------------------------------
        return get_order_from_primary.invoke({
            "order_id": order_id
        })

    except Exception as e:

        print("Primary system failed:", e)
        print("Using backup order system...")

        # ---------------------------------------------
        # Fallback
        # ---------------------------------------------
        return get_order_from_backup.invoke({
            "order_id": order_id
        })


# =========================================================
# Order Cancellation
# =========================================================

@tool
def cancel_order(order_id: str):
    """Cancel an order."""

    return f"Order {order_id} has been cancelled."


tools = [
    get_order,
    cancel_order
]


# =========================================================
# Prompt Guardrails
# =========================================================

SYSTEM_PROMPT = """
You are an enterprise order processing assistant.

Follow these rules:

1. Always use get_order() to retrieve order information.
2. Never invent order information.
3. Never cancel an order unless its current status is known.
4. Do not cancel an order that is already DELIVERED.
5. If order information cannot be retrieved, explain the problem
   instead of guessing.
"""


# =========================================================
# LLM
# =========================================================

load_dotenv()

llm = ChatOpenAI(
    model=os.environ["MODEL_NAME"]
)


# =========================================================
# Agent
# =========================================================

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT
)


# =========================================================
# Invoke
# =========================================================

result = agent.invoke({
    "messages": [
        {
            "role": "user",
            "content":
                "Check ORD1001 and tell me its current status."
        }
    ]
})

print("\nFinal Answer:")
print(result["messages"][-1].content)