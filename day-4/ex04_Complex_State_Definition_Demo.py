from typing import Annotated, TypedDict
import operator

from langgraph.graph import StateGraph, START, END


# ---------------------------------------------------------
# Custom State
# ---------------------------------------------------------

class OrderState(TypedDict):
    order_id: str
    status: str

    messages: Annotated[
        list[str],
        operator.add
    ]
    # messages: list[str]


# ---------------------------------------------------------
# Nodes
# ---------------------------------------------------------

def validate_order(state: OrderState):
    return {
        "status": "VALID",
        "messages": [
            "Order is valid"
        ]
    }


def check_inventory(state: OrderState):
    return {
        "messages": [
            "Inventory is available"
        ]
    }


def check_payment(state: OrderState):
    return {
        "messages": [
            "Payment is successful"
        ]
    }


# ---------------------------------------------------------
# Build Graph
# ---------------------------------------------------------

graph = StateGraph(OrderState)

graph.add_node("validate", validate_order)
graph.add_node("inventory", check_inventory)
graph.add_node("payment", check_payment)

graph.add_edge(START, "validate")
graph.add_edge("validate", "inventory")
graph.add_edge("inventory", "payment")
graph.add_edge("payment", END)

app = graph.compile()


# ---------------------------------------------------------
# Run
# ---------------------------------------------------------

result = app.invoke({
    "order_id": "ORD1001",
    "status": "NEW",
    "messages": []
})

print(result)