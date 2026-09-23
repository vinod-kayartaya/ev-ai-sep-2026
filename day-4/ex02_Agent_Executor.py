import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate


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


# ---------------------------------------------------------
# Prompt
# ---------------------------------------------------------

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an order processing assistant. "
        "Use the available tools when necessary."
    ),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])


# ---------------------------------------------------------
# Create Agent
# ---------------------------------------------------------

agent = create_tool_calling_agent(
    llm,
    tools,
    prompt
)


# ---------------------------------------------------------
# AgentExecutor
# ---------------------------------------------------------

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True
)


# ---------------------------------------------------------
# Invoke
# ---------------------------------------------------------

result = agent_executor.invoke({
    "input":
        "Check order ORD1001 and cancel it if it has not been delivered."
})

print("\nFinal Answer:")
print(result["output"])