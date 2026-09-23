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


def create_ticket_processor_graph(llm):

    # state of the graph (an object of this is received by all nodes of this graph)
    class State(TypedDict):
        complaint: str
        category: str
        response: str

    # node 1 - identify the category of complaint
    def identify_complaint_category(state: State):
        category = llm.invoke(
            f"""categorize the following complaint as exactly one of these - PAYMENT,QUALITY,DELIVERY. (Give exactly one word in uppercase):

            Complaint:
            {state["complaint"]}
            """
        ).content

        return {
            "category": category
        }

    def payment_node(state: State) -> State:
        return {
            "response": "We have forwared your complaint to the payment deparment"
        }

    def delivery_node(state: State) -> State:
        return {
            "response": "We have forwared your complaint to the delevery deparment"
        }

    def quality_node(state: State) -> State:
        return {
            "response": "We have forwared your complaint to the quality deparment"
        }

    def send_email_response(state: State) -> State:
        print("Sending email is not available yet")
        return {}

    # this will be used/configured as a conditional edge
    # argument is always the state
    # returns always a str (which is the discriminator)
    def routing_logic(state: State) -> str:
        if state["category"] == "PAYMENT":
            return "payment-issue"
        if state["category"] == "DELIVERY":
            return "delivery-issue"
        if state["category"] == "QUALITY":
            return "quality-issue"

        raise ValueError(f"Invalid category encountered - {state["category"]}")

    builder = StateGraph(State)
    builder.add_node(identify_complaint_category)
    builder.add_node(payment_node)
    builder.add_node(delivery_node)
    builder.add_node(quality_node)
    builder.add_node(send_email_response)

    builder.add_edge(START, "identify_complaint_category")
    builder.add_conditional_edges(
        "identify_complaint_category",          # FROM THIS NODE
        routing_logic,                          # TO THIS CONDITIONAL EDGE FUNCTION
        {
            # discriminator --> node name
            "payment-issue": "payment_node",    # TO THIS NODE
            "delivery-issue": "delivery_node",  # OR TO THIS NODE
            "quality-issue": "quality_node",    # OR TO THIS NODE
        }
    )
    builder.add_edge("payment_node", "send_email_response")
    builder.add_edge("delivery_node", "send_email_response")
    builder.add_edge("quality_node", "send_email_response")
    builder.add_edge("send_email_response", END)


    return builder.compile()



def main():
    init()
    llm = ChatOpenAI(model=model_name)
    app = create_ticket_processor_graph(llm)
    app.get_graph().draw_png(output_file_path="./example.png")
    

    initial_state = {
        "complaint": input("Enter your complaint: ")
    }
    result = app.invoke(initial_state)
    print(f"{result["category"] = }")
    print(f"{result["response"] = }")


if __name__ == "__main__":
    main()