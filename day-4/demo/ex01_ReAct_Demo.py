import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage


# ---------------------------------------------------------
# Tools
# ---------------------------------------------------------

@tool
def get_order(order_id: str):
    """Get the details of an order."""

    orders = {
        "ORD1001": {
            "status": "SHIPPED",
            "customer": "John",
            "amount": 2500
        },
        "ORD1002": {
            "status": "DELIVERED",
            "customer": "Alice",
            "amount": 1800
        }
    }

    return orders.get(order_id, "Order not found")


@tool
def cancel_order(order_id: str):
    """Cancel an order."""

    return f"Order {order_id} has been cancelled."


tools = [get_order, cancel_order]


# ---------------------------------------------------------
# LLM
# ---------------------------------------------------------

load_dotenv()

llm = ChatOpenAI(
    model=os.environ["MODEL_NAME"]
)

llm_with_tools = llm.bind_tools(tools)


# ---------------------------------------------------------
# ReAct loop
# ---------------------------------------------------------

messages = [
    HumanMessage(
        content="Check order ORD1001 and cancel it if it has not been delivered."
    )
]

while True:

    # ---------------------------------------------
    # REASON
    # ---------------------------------------------
    response = llm_with_tools.invoke(messages)

    messages.append(response)

    print("\nLLM:")
    print(response.content)

    # ---------------------------------------------
    # Check whether the LLM wants to perform ACTION
    # ---------------------------------------------
    if not response.tool_calls:
        print("\nFinal Answer:")
        print(response.content)
        break

    # ---------------------------------------------
    # ACTION
    # ---------------------------------------------
    for tool_call in response.tool_calls:

        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        print("\nACTION:")
        print(tool_name, tool_args)

        # Find the requested tool
        selected_tool = next(
            tool for tool in tools
            if tool.name == tool_name
        )

        # Execute the tool
        result = selected_tool.invoke(tool_args)

        print("OBSERVATION:")
        print(result)

        # -----------------------------------------
        # Add the observation back to the messages
        # -----------------------------------------
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": str(result)
            }
        )