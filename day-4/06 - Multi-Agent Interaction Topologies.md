# Multi-Agent Handoffs with LangGraph

A multi-agent system consists of multiple specialized agents that collaborate to solve a problem.

Consider an order-processing system with:

- **Order Agent** — handles general order requests.
- **Payment Agent** — handles payment-related issues.

The interesting part is not simply having two agents. It is allowing one agent to **decide when another agent should take over**.

## 1. Traditional Conditional Routing

A simple LangGraph workflow can use a router:

```text id="d4lq0m"
             Router
            /      \
           ↓        ↓
       Order      Payment
       Agent       Agent
```

The application contains the routing logic:

```python
if request_is_about_payment:
    return "payment"
```

This is centralized routing.

The agents themselves do not decide who should handle the request.

## 2. Agent-Based Handoff

In a multi-agent design, the Order Agent can analyze the request and decide whether another agent should handle it:

```text id="k8h8j6"
Customer Request
       |
       v
  Order Agent
       |
       | LLM reasoning
       |
       +---- payment issue ----> Payment Agent
       |
       +---- order issue ------> Order Agent
```

The Order Agent is therefore participating in the routing decision.

## 3. Agent State

A simple shared state can contain:

```python
class OrderState(TypedDict):
    order_id: str
    message: str
    response: str
    next_agent: str
```

The state is passed between agents.

For example:

```text id="yq7u0c"
{
    order_id: "ORD1001",
    message: "I was charged twice",
    ...
}
```

The Payment Agent can use the same `order_id` when it receives the handoff.

## 4. Let the LLM Decide

The Order Agent can ask the LLM to classify the request:

```python
prompt = f"""
You are an Order Agent.

Customer request:
{state["message"]}

If this is payment-related, respond:
HANDOFF:PAYMENT

Otherwise respond:
HANDLE:ORDER
"""
```

The LLM might return:

```text
HANDOFF:PAYMENT
```

The Order Agent converts this into a routing decision:

```python
if decision == "HANDOFF:PAYMENT":
    return {"next_agent": "payment"}
```

The important point is that the **semantic decision** came from the agent.

## 5. LangGraph Executes the Handoff

LangGraph can then use the agent's decision:

```python
builder.add_conditional_edges(
    "order_agent",
    route_from_order,
    {
        "order": END,
        "payment": "payment_agent"
    }
)
```

The resulting execution is:

```text id="8exl0w"
START
  |
  v
Order Agent
  |
  | "HANDOFF:PAYMENT"
  v
Payment Agent
  |
  v
 END
```

LangGraph provides the execution mechanism, while the agent provides the decision.

## 6. Why This Is a Multi-Agent Pattern

The distinction is important.

In a conventional workflow:

```text id="7eqx3h"
Application Router
       |
       +----> Agent A
       |
       +----> Agent B
```

The router knows about the agents and decides where to send the request.

In a handoff-based system:

```text id="m6p5tc"
Agent A
   |
   | "This requires Agent B"
   v
Agent B
```

Agent A determines that another specialist is required.

This allows more dynamic collaboration.

## 7. Multiple Handoffs

The pattern can be extended:

```text id="7k0vha"
             Order Agent
             /         \
            ↓           ↓
      Payment Agent   Support Agent
            |
            ↓
      Fraud Agent
```

For example:

```text
Order Agent
    ↓
Payment Agent
    ↓
Fraud Agent
```

Each agent can specialize in a particular responsibility.

## 8. Shared vs. Isolated Context

Agents can share the same LangGraph state:

```text id="h1q3qk"
             Shared State
            /     |      \
           ↓      ↓       ↓
        Order  Payment  Support
```

Alternatively, an application can provide each agent with only the information it requires.

For example, the Payment Agent might receive:

```python
{
    "order_id": "ORD1001",
    "payment_issue": "charged twice"
}
```

rather than the entire conversation.

This creates stronger separation between agents.

## 9. Centralized vs. Peer-to-Peer

These are two different topologies.

**Centralized orchestration:**

```text id="2v8kq1"
          Supervisor
          /   |   \
         ↓    ↓    ↓
      Order Payment Support
```

**Peer-to-peer handoff:**

```text id="z8c4mw"
Order
  |
  ↓
Payment
  |
  ↓
Support
```

The first uses a central decision-maker.

The second allows agents to transfer responsibility to one another.

## 10. Key Takeaway

The important concept is not simply "multiple agents."

It is **delegation between specialized agents**.

```text id="9j2y7x"
User Request
     ↓
Order Agent
     ↓
Reason about request
     ↓
Need another specialist?
     ↓
   Yes
     ↓
Handoff
     ↓
Payment Agent
```

LangGraph provides the graph structure, state management, and execution flow. The LLM-powered agents provide the reasoning that determines when a handoff should occur.

This combination allows a workflow to move from **fixed routing** toward **dynamic multi-agent collaboration**.
