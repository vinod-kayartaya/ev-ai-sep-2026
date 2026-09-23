# Standard `AgentExecutor` Usage and Limitations

## 1. Introduction

A ReAct-style agent repeatedly follows this pattern:

```text
Reason
  ↓
Action
  ↓
Observation
  ↓
Reason
  ↓
...
```

The application needs something to manage this loop: invoke the agent, execute its tool calls, provide the results back, and continue until the agent produces a final answer.

In traditional LangChain agent implementations, **`AgentExecutor`** performs this role.

---

## 2. Order Processing Example

Consider an order processing system with two tools:

```python
@tool
def get_order(order_id: str):
    """Get order details."""
    orders = {
        "ORD1001": {
            "status": "SHIPPED",
            "customer": "John"
        },
        "ORD1002": {
            "status": "DELIVERED",
            "customer": "Alice"
        }
    }

    return orders.get(order_id, "Order not found")


@tool
def cancel_order(order_id: str):
    """Cancel an order."""
    return f"Order {order_id} has been cancelled."
```

The user can then ask:

```text
Check order ORD1001 and cancel it if it has not been delivered.
```

The agent needs to:

1. Call `get_order()`.
2. Examine the returned status.
3. Decide whether cancellation is required.
4. Call `cancel_order()` if appropriate.
5. Produce the final response.

---

## 3. Creating the Agent

The LLM and tools are first used to create an agent:

```python
agent = create_tool_calling_agent(
    llm,
    tools,
    prompt
)
```

The agent determines **what action should be taken**.

Next, the agent is given to `AgentExecutor`:

```python
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True
)
```

The application can then invoke it:

```python
result = agent_executor.invoke({
    "input":
        "Check order ORD1001 and cancel it if it has not been delivered."
})

print(result["output"])
```

---

## 4. What `AgentExecutor` Does

Conceptually, `AgentExecutor` manages the ReAct loop:

```text
                 User Request
                      |
                      v
                    Agent
                      |
                      v
                  Tool Call
                      |
                      v
                AgentExecutor
                      |
                      v
                 Execute Tool
                      |
                      v
                 Tool Result
                      |
                      v
                    Agent
                      |
                      v
                 Tool Call
                      |
                     ...
                      |
                      v
                 Final Answer
```

For the order example:

```text
Agent
  |
  | get_order("ORD1001")
  v
AgentExecutor
  |
  v
status = SHIPPED
  |
  v
Agent
  |
  | cancel_order("ORD1001")
  v
AgentExecutor
  |
  v
Cancellation successful
  |
  v
Final Answer
```

The important point is that the application does **not** have to manually implement every iteration of the loop.

---

## 5. Why `AgentExecutor` Is Convenient

For relatively simple agent tasks, this model is convenient because the executor handles the repetitive mechanics:

```text
Invoke agent
    ↓
Check for tool call
    ↓
Execute tool
    ↓
Return result to agent
    ↓
Repeat
```

The developer can therefore focus mainly on:

* defining the tools
* defining the prompt
* configuring the LLM
* defining the desired agent behavior

---

## 6. Limitations

`AgentExecutor` works well for straightforward agent loops, but complex workflows can become difficult to control explicitly.

Consider a more complicated order workflow:

```text
Get Order
    |
    v
Check Payment
    |
    +---- Failed ------> Stop
    |
    v
Check Inventory
    |
    +---- Unavailable -> Notify Customer
    |
    v
Process Order
    |
    v
Update Database
```

There are now explicit:

* branches
* conditions
* state changes
* error paths
* retries
* business rules

A general-purpose agent loop can handle some of these decisions, but the workflow structure is not explicitly represented in the same way as a graph.

This can make complex workflows harder to:

* visualize
* control
* debug
* test
* enforce deterministically

---

## 7. AgentExecutor vs. Explicit Workflows

A simple agent loop can be represented as:

```text
Agent
  ↓
Tool
  ↓
Agent
  ↓
Tool
  ↓
Agent
```

This is flexible because the agent decides what to do next.

A structured workflow can instead explicitly define its paths:

```text
             Get Order
                 |
                 v
           Check Payment
             /       \
        Failed       Success
          |             |
         Stop     Check Inventory
                       /     \
                Available   Unavailable
                    |           |
               Process       Notify
```

The second approach provides more explicit control over the workflow.

This is one of the motivations for using **LangGraph** when agent applications become stateful and workflow-heavy.

---

## 8. Key Takeaway

`AgentExecutor` is the traditional mechanism for executing an agent's iterative tool-calling loop.

Its conceptual responsibility is:

```text
Agent
  ↓
Action
  ↓
Tool
  ↓
Observation
  ↓
Agent
  ↓
...
  ↓
Final Answer
```

It is convenient for relatively simple ReAct-style agents.

As the application requires increasingly explicit **state, branching, retries, conditions, and workflow control**, a graph-based approach such as LangGraph provides a more explicit way to model those behaviors.

> **AgentExecutor manages the agent loop; the agent decides the next action.**
