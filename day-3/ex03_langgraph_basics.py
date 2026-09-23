from langgraph.graph import START, END, StateGraph
from typing import TypedDict


class UserComplaint(TypedDict):
    complaint: str
    response: str


def process_user_complaint(state: UserComplaint) -> UserComplaint:
    print(f"[DEBUG] user complained as {state["complaint"]}")
    return {
        "response": "We will get back to you soon."
    }


builder = StateGraph(UserComplaint)

# add all nodes
builder.add_node("handle_complaint", process_user_complaint)

# add all edges (connect nodes with edges)
builder.add_edge(START, "handle_complaint")
builder.add_edge("handle_complaint", END)

# build (compile) the graph
graph = builder.compile()

# invoke the graph (by supplying the initial state)
initial_state = {"complaint": "I ordered a footwear and the size was wrong"}
result = graph.invoke(initial_state)
print(result)