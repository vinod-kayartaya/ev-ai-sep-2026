import os
import sys
from dotenv import load_dotenv

from typing import TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph import START, END, StateGraph


def init():
    global model_name
    load_dotenv()   # loads environment variables from .env file
    model_name = os.environ.get("OPENAI_MODEL_NAME")
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required, but missing!")
        sys.exit(1)

init()
llm = ChatOpenAI(model=model_name)

class State(TypedDict):
    complaint: str
    category: str
    response: str


# node 1 - identify the category of complaint
def identify_complaint_category(state: State):
    category = llm.invoke(
        f"""categorize the following complaint as exactly one of these - PAYMENT,QUALITY,DELIVERY,UNCATEGORIZED (Give exactly one word in uppercase):

        Complaint:
        {state["complaint"]}
        """
    ).content

    return {
        "category": category
    }

    
# node 2 - generate a response for the complaint
def generate_complaint_response(state: State):
    response = llm.invoke(
        f"""Generate a one sentence response to be given to the customer regarding the complaint raised by them.

        Category: {state["category"]}
        Complaint: {state["complaint"]}
        """
    ).content

    return {
        "response": response
    }


def main():
    builder = StateGraph(State)
    builder.add_node(identify_complaint_category)
    builder.add_node(generate_complaint_response)

    builder.add_edge(START, "identify_complaint_category")
    builder.add_edge("identify_complaint_category", "generate_complaint_response")
    builder.add_edge("generate_complaint_response", END)

    app = builder.compile()     # create the graph
    initial_state = {"complaint": input("Enter your complaint: ")}
    final_state = app.invoke(initial_state)

    print(final_state)


if __name__ == "__main__":
    main()