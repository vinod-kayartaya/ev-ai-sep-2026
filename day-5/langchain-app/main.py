#!/usr/bin/env python3
"""
AI Customer Complaint Resolution CLI Application
Built with LangGraph, LangChain, and Langfuse @observe Observability.

Academic Example:
Demonstrates how to use Langfuse's `@observe` decorator to instrument
LangGraph nodes and trace LLM workflows without needing CallbackHandler objects.
All executable setup code is encapsulated in functions.
"""

import os
import sys
from typing import Literal, Optional, TypedDict
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langfuse import Langfuse, observe
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

# Module-level variable references (populated by init())
base_url: Optional[str] = None
model_name: Optional[str] = None
langfuse_client: Optional[Langfuse] = None
llm: Optional[ChatOpenAI] = None
graph = None


# ------------------------------------------------------------------------------
# 1. Environment & Observability Setup
# ------------------------------------------------------------------------------
def init():
    """
    Initializes environment variables, Langfuse client, OpenAI model,
    and compiles the LangGraph workflow.
    """
    global base_url, model_name, langfuse_client, llm, graph

    # Load environment variables from .env file
    load_dotenv()

    # Set endpoint URLs for Langfuse
    base_url = os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST") or "http://localhost:3000"
    os.environ["LANGFUSE_HOST"] = base_url
    os.environ["LANGFUSE_BASEURL"] = base_url

    # Initialize the Langfuse client
    langfuse_client = Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=base_url
    )

    # Initialize OpenAI Model
    model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    llm = ChatOpenAI(
        model=model_name,
        temperature=0.3,
        api_key=os.getenv("OPENAI_API_KEY")
    )

    # Compile the LangGraph state machine
    graph = build_complaint_graph()

    # Generate graph PNG diagram if it does not already exist
    png_path = os.path.join(os.path.dirname(__file__), "complaint_graph.png")
    if not os.path.exists(png_path):
        save_graph_png(png_path)


# ------------------------------------------------------------------------------
# 2. State & Data Models
# ------------------------------------------------------------------------------
class ComplaintCategorySchema(BaseModel):
    """Structured classification output schema."""
    category: Literal["Payment", "Quality", "Delivery", "Uncategorized"] = Field(
        description=(
            "Must be strictly one of: Payment, Quality, Delivery, or Uncategorized. "
            "Choose Uncategorized if the complaint is unclear, vague, unrelated to an e-commerce order "
            "(e.g., greetings, general questions, gibberish), or cannot be categorized as Payment, Quality, or Delivery."
        )
    )
    reasoning: str = Field(
        description="A concise sentence explaining why this category was chosen."
    )


class ComplaintState(TypedDict):
    """State passed between LangGraph nodes."""
    complaint: str
    category: Optional[Literal["Payment", "Quality", "Delivery", "Uncategorized"]]
    reasoning: Optional[str]
    response: Optional[str]


# ------------------------------------------------------------------------------
# 3. LangGraph Nodes (Instrumented with @observe)
# ------------------------------------------------------------------------------
# NOTE:
# By simply adding the `@observe()` decorator above each node function,
# Langfuse automatically tracks:
#   1. Node execution start and end times (latency)
#   2. Input state received by the node
#   3. Output dictionary returned by the node
#   4. Any errors or exceptions raised during execution

@observe(name="categorize_complaint")
def categorize_complaint(state: ComplaintState) -> dict:
    """
    Classifier Node:
    Analyzes the customer complaint and assigns it to Payment, Quality, Delivery,
    or Uncategorized if it cannot be classified into the known categories.
    """
    complaint = state["complaint"]
    
    classifier_llm = llm.with_structured_output(ComplaintCategorySchema)
    
    system_prompt = (
        "You are an expert customer service triage specialist for an e-commerce platform.\n"
        "Analyze the customer's input and categorize it into exactly one of four categories:\n"
        "- Payment: Issues regarding billing, charged twice, deductions, payment gateway failures, refunds, card declined, invoice errors.\n"
        "- Quality: Issues regarding defective items, damaged packaging/product, expired goods, wrong color/size received, broken items, missing accessories.\n"
        "- Delivery: Issues regarding delayed shipments, tracking not updating, courier behavior, package delivered to wrong address, missing deliveries.\n"
        "- Uncategorized: The message cannot be understood, is ambiguous, gibberish, general conversation, or does not clearly relate to a payment, quality, or delivery issue for a placed order.\n"
        "Be accurate and objective. Do not force an unrelated or ambiguous input into Payment, Quality, or Delivery."
    )
    
    result = classifier_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Customer Complaint:\n\"{complaint}\"")
    ])
    
    return {
        "category": result.category,
        "reasoning": result.reasoning
    }


@observe(name="handle_payment_issue")
def handle_payment_issue(state: ComplaintState) -> dict:
    """
    Payment Specialist Node:
    Generates an empathetic, actionable response for billing and payment inquiries.
    """
    complaint = state["complaint"]
    
    system_prompt = (
        "You are a Senior Payment & Billing Support Specialist.\n"
        "Draft an empathetic, reassuring, and professional response to the customer's payment/refund issue.\n"
        "Your response must:\n"
        "1. Acknowledge and apologize for the financial anxiety/inconvenience caused.\n"
        "2. Explain clear next steps (e.g., verifying transaction IDs, refund turnaround time of 3-5 business days).\n"
        "3. Provide guidance on what details they should keep ready (e.g., order ID, transaction reference).\n"
        "4. Keep a courteous, warm, and professional tone."
    )
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Customer Complaint:\n\"{complaint}\"")
    ])
    
    return {"response": response.content}


@observe(name="handle_quality_issue")
def handle_quality_issue(state: ComplaintState) -> dict:
    """
    Quality Assurance Specialist Node:
    Generates an empathetic, resolution-focused response for product defects or damage.
    """
    complaint = state["complaint"]
    
    system_prompt = (
        "You are a Quality Assurance & Customer Experience Specialist.\n"
        "Draft an empathetic, apologetic, and resolution-focused response to a customer facing product quality or damage issues.\n"
        "Your response must:\n"
        "1. Sincerely apologize that the product did not meet our high quality standards.\n"
        "2. Offer immediate options: a free replacement or a full refund/store credit upon return.\n"
        "3. Explain the simple return/exchange process (e.g., photos of damage, complimentary pickup).\n"
        "4. Reassure the customer that this feedback has been flagged to our quality inspection team."
    )
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Customer Complaint:\n\"{complaint}\"")
    ])
    
    return {"response": response.content}


@observe(name="handle_delivery_issue")
def handle_delivery_issue(state: ComplaintState) -> dict:
    """
    Logistics & Delivery Specialist Node:
    Generates an informative, reassuring response for shipping and transit problems.
    """
    complaint = state["complaint"]
    
    system_prompt = (
        "You are a Logistics & Fulfillment Support Specialist.\n"
        "Draft an understanding, proactive, and clear response to a customer experiencing delivery delays or shipping problems.\n"
        "Your response must:\n"
        "1. Validate their frustration regarding delayed or mishandled delivery.\n"
        "2. Explain that logistics operations are actively investigating with the courier partner.\n"
        "3. Provide an immediate timeline for follow-up (e.g., within 24 hours with an updated delivery ETA).\n"
        "4. Offer support options (e.g., priority dispatch or cancellation/reshipment if the package is deemed lost)."
    )
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Customer Complaint:\n\"{complaint}\"")
    ])
    
    return {"response": response.content}


@observe(name="handle_uncategorized_issue")
def handle_uncategorized_issue(state: ComplaintState) -> dict:
    """
    Uncategorized Specialist Node:
    Informs the customer that their message could not be categorized under supported
    order issues and requests them to re-input with details related to the order they placed.
    """
    complaint = state["complaint"]

    system_prompt = (
        "You are a Customer Support Assistant for an e-commerce platform.\n"
        "The customer provided an inquiry or complaint that could not be understood or does not match our supported categories (Payment, Quality, or Delivery issues for an order).\n"
        "Draft a polite, helpful response that:\n"
        "1. Respectfully informs them that we could not understand or categorize their issue based on the provided message.\n"
        "2. Clearly asks the customer to re-enter their complaint with specific details related to an order they placed.\n"
        "3. Provides helpful examples of what they can raise (e.g., payment or refund issues, damaged/defective product quality, or shipping/delivery delays).\n"
        "4. Encourages them to include an Order ID or item details so we can assist them immediately.\n"
        "Maintain a professional, polite, and encouraging tone."
    )

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Customer Input:\n\"{complaint}\"")
    ])

    return {"response": response.content}


# ------------------------------------------------------------------------------
# 4. Routing Logic
# ------------------------------------------------------------------------------
def route_by_category(state: ComplaintState) -> Literal["handle_payment", "handle_quality", "handle_delivery", "handle_uncategorized"]:
    """Conditional edge router based on classified category."""
    category = state.get("category")
    if category == "Payment":
        return "handle_payment"
    elif category == "Quality":
        return "handle_quality"
    elif category == "Delivery":
        return "handle_delivery"
    return "handle_uncategorized"


# ------------------------------------------------------------------------------
# 5. Build and Compile the LangGraph Workflow
# ------------------------------------------------------------------------------
def build_complaint_graph():
    """Builds and compiles the StateGraph workflow."""
    workflow = StateGraph(ComplaintState)

    # Add Nodes
    workflow.add_node("categorize", categorize_complaint)
    workflow.add_node("handle_payment", handle_payment_issue)
    workflow.add_node("handle_quality", handle_quality_issue)
    workflow.add_node("handle_delivery", handle_delivery_issue)
    workflow.add_node("handle_uncategorized", handle_uncategorized_issue)

    # Set Entry Point
    workflow.set_entry_point("categorize")

    # Add Conditional Edges
    workflow.add_conditional_edges(
        "categorize",
        route_by_category,
        {
            "handle_payment": "handle_payment",
            "handle_quality": "handle_quality",
            "handle_delivery": "handle_delivery",
            "handle_uncategorized": "handle_uncategorized"
        }
    )

    # Connect handler nodes to END
    workflow.add_edge("handle_payment", END)
    workflow.add_edge("handle_quality", END)
    workflow.add_edge("handle_delivery", END)
    workflow.add_edge("handle_uncategorized", END)

    return workflow.compile()


def save_graph_png(output_path: str = "complaint_graph.png"):
    """
    Exports a visual PNG diagram of the compiled LangGraph workflow.
    Uses LangGraph's built-in draw_mermaid_png() method.
    """
    if graph is None:
        return
    try:
        png_data = graph.get_graph().draw_mermaid_png()
        with open(output_path, "wb") as f:
            f.write(png_data)
    except Exception as e:
        print(f"[Warning] Could not export graph image: {e}")


# ------------------------------------------------------------------------------
# 6. Process Complaint Function (Root @observe trace)
# ------------------------------------------------------------------------------
@observe(name="process_customer_complaint")
def process_complaint(complaint_text: str):
    """
    Root function for processing a customer complaint.
    Decorated with @observe so it creates the root trace in Langfuse.
    All child nodes executed inside LangGraph are automatically nested under this trace.
    """
    complaint_text = complaint_text.strip()
    if not complaint_text:
        print("\n[!] Complaint text cannot be empty.\n", file=sys.stderr)
        return

    print("\n" + "=" * 70)
    print(f"Processing Complaint: \"{complaint_text}\"")
    print("=" * 70)

    try:
        # Note: No callback config needed here!
        # The @observe decorator on the nodes automatically handles tracing.
        final_state = graph.invoke({"complaint": complaint_text})

        category = final_state.get("category", "Unknown")
        reasoning = final_state.get("reasoning", "N/A")
        response = final_state.get("response", "No response generated.")

        # Print outputs directly to STDOUT
        print(f"\nDetected Category : {category}")
        print(f"Category Reasoning : {reasoning}")
        print("\n" + "-" * 70)
        print("Generated Response :")
        print("-" * 70)
        print(response)
        print("-" * 70)

        # Flush events to Langfuse so they appear immediately in the UI
        langfuse_client.flush()
        print(f"\nTrace sent to Langfuse ({base_url})")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n[Error] Error processing complaint: {e}\n", file=sys.stderr)
        if langfuse_client:
            langfuse_client.flush()


# ------------------------------------------------------------------------------
# 7. Interactive CLI Entry Point (No argparse)
# ------------------------------------------------------------------------------
def main():
    """Initializes the environment and starts the interactive CLI loop."""
    # Initialize environment, Langfuse, model, and graph
    init()

    print("=" * 70)
    print("Customer Complaint AI Resolution CLI")
    print(f"Langfuse Observability: Enabled via @observe ({base_url})")
    print(f"LLM Engine: {model_name}")
    print("=" * 70)
    print("Enter a customer complaint below (or type 'exit' / 'quit' to quit):\n")

    while True:
        try:
            user_input = input("Customer Complaint > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("\nGoodbye!")
                break
            process_complaint(user_input)
        except (KeyboardInterrupt, EOFError):
            print("\n\nSession ended. Goodbye!")
            break


if __name__ == "__main__":
    main()
