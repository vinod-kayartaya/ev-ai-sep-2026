from typing import TypedDict

from langgraph.graph import StateGraph, START, END


# =========================================================
# Parent State
# =========================================================

class OrderState(TypedDict):
    order_id: str
    amount: float
    status: str
    order_result: str
    payment_result: str
    final_result: str


# =========================================================
# ORDER TEAM - SUB-GRAPH
# =========================================================

class OrderTeamState(TypedDict):
    order_id: str
    amount: float
    result: str


def validate_order(state: OrderTeamState):

    print("Order Team: validating order...")

    if state["amount"] <= 100000:
        result = "Order is valid"
    else:
        result = "Order requires additional review"

    return {
        "result": result
    }


order_builder = StateGraph(OrderTeamState)

order_builder.add_node(
    "validate",
    validate_order
)

order_builder.add_edge(
    START,
    "validate"
)

order_builder.add_edge(
    "validate",
    END
)

order_team = order_builder.compile()

order_team.get_graph().draw_png(output_file_path="order_team.png")
# =========================================================
# PAYMENT TEAM - SUB-GRAPH
# =========================================================

class PaymentTeamState(TypedDict):
    order_id: str
    amount: float
    result: str


def check_payment(state: PaymentTeamState):

    print("Payment Team: checking payment...")

    if state["amount"] <= 50000:
        result = "Payment successful"
    else:
        result = "Payment requires verification"

    return {
        "result": result
    }


payment_builder = StateGraph(PaymentTeamState)

payment_builder.add_node(
    "check_payment",
    check_payment
)

payment_builder.add_edge(
    START,
    "check_payment"
)

payment_builder.add_edge(
    "check_payment",
    END
)

payment_team = payment_builder.compile()


# =========================================================
# PARENT GRAPH
# =========================================================

def run_order_team(state: OrderState):

    result = order_team.invoke({
        "order_id": state["order_id"],
        "amount": state["amount"],
        "result": ""
    })

    return {
        "order_result": result["result"]
    }


def run_payment_team(state: OrderState):

    result = payment_team.invoke({
        "order_id": state["order_id"],
        "amount": state["amount"],
        "result": ""
    })

    return {
        "payment_result": result["result"]
    }


def finalize(state: OrderState):

    print("Parent graph: combining team results...")

    return {
        "final_result": (
            f"Order: {state['order_result']}\n"
            f"Payment: {state['payment_result']}"
        ),
        "status": "COMPLETED"
    }


parent_builder = StateGraph(OrderState)

parent_builder.add_node(
    "order_team",
    run_order_team
)

parent_builder.add_node(
    "payment_team",
    run_payment_team
)

parent_builder.add_node(
    "finalize",
    finalize
)

parent_builder.add_edge(
    START,
    "order_team"
)

parent_builder.add_edge(
    "order_team",
    "payment_team"
)

parent_builder.add_edge(
    "payment_team",
    "finalize"
)

parent_builder.add_edge(
    "finalize",
    END
)

graph = parent_builder.compile()
graph.get_graph().draw_png(output_file_path="ex8.png")
exit(0)


# =========================================================
# RUN
# =========================================================

result = graph.invoke({
    "order_id": "ORD1001",
    "amount": 25000,
    "status": "NEW",
    "order_result": "",
    "payment_result": "",
    "final_result": ""
})

print("\nFinal result:")
print(result["final_result"])