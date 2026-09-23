import os
import sys
from dotenv import load_dotenv

from typing import TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph import START, END, StateGraph

load_dotenv()   # loads environment variables from .env file
model_name = os.environ.get("OPENAI_MODEL_NAME")
if not os.environ.get("OPENAI_API_KEY"):
    print("OPENAI_API_KEY is required, but missing!")
    sys.exit(1)

llm = ChatOpenAI(model=model_name)

class State(TypedDict):
    complaint: str
    draft: str
    review: str
    approved: bool
    iteration: int
    final_response: str

def draft_response(state: State):

    response = llm.invoke(f"""
Write a professional customer-support response.

Complaint:
{state["complaint"]}
""")

    return {
        "draft": response.content,
        "iteration": 1
    }

def review_response(state: State):

    response = llm.invoke(f"""
Review this customer-support response.

Complaint:
{state["complaint"]}

Draft:
{state["draft"]}

Determine whether the response is acceptable.

Return either:

APPROVED

or:

NEEDS_WORK
followed by feedback.
""")

    review = response.content

    approved = (
        review.strip()
        .upper()
        .startswith("APPROVED")
    )

    return {
        "review": review,
        "approved": approved
    }


def revise_response(state: State):

    response = llm.invoke(f"""
Improve this response.

Complaint:
{state["complaint"]}

Current response:
{state["draft"]}

Review:
{state["review"]}

Return only the revised response.
""")

    return {
        "draft": response.content,
        "iteration": state["iteration"] + 1
    }


def route_after_review(state: State):

    if state["approved"]:
        return "finalize"

    if state["iteration"] >= 3:
        return "finalize"

    return "revise"


def finalize(state: State):
    return {}

builder = StateGraph(State)

builder.add_node("draft", draft_response)
builder.add_node("review", review_response)
builder.add_node("revise", revise_response)
builder.add_node("finalize", finalize)

builder.add_edge(START, "draft")
builder.add_edge("draft", "review")

builder.add_conditional_edges(
    "review",
    route_after_review,
    {
        "finalize": "finalize",
        "revise": "revise"
    }
)

builder.add_edge(
    "revise",
    "review"
)

builder.add_edge(
    "finalize",
    END
)

graph = builder.compile()
graph.get_graph().draw_png(output_file_path="./example5.png")
