"""
RAG Engine module using LangChain, LangGraph, OpenAI, and Langfuse observability.
Retrieves relevant historical customer support tickets from SQLite and generates
grounded, context-aware responses with conversation history support.
"""

import os
import sys
from typing import List, Dict, Any, Optional, TypedDict
import numpy as np
from dotenv import load_dotenv

# Ensure local and parent directories are in search path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, CURRENT_DIR)

# Load environment configuration
load_dotenv(os.path.join(CURRENT_DIR, ".env"))
if not os.getenv("OPENAI_API_KEY"):
    load_dotenv(os.path.join(PARENT_DIR, "langchain-app", ".env"))

import database
from langfuse import Langfuse, observe
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END

# --- Module Globals & Initialization ---
llm: Optional[ChatOpenAI] = None
embeddings_model: Optional[OpenAIEmbeddings] = None
langfuse_client: Optional[Langfuse] = None
rag_graph = None


def init_rag_engine():
    """Initializes LLM, Embeddings, Langfuse client, and LangGraph workflow."""
    global llm, embeddings_model, langfuse_client, rag_graph

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in environment or .env file.")

    model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")

    # Langfuse configuration
    langfuse_base = os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST") or "http://localhost:3000"
    os.environ["LANGFUSE_HOST"] = langfuse_base
    os.environ["LANGFUSE_BASEURL"] = langfuse_base
    
    pub_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    sec_key = os.getenv("LANGFUSE_SECRET_KEY")
    if pub_key and sec_key:
        try:
            langfuse_client = Langfuse(
                public_key=pub_key,
                secret_key=sec_key,
                host=langfuse_base
            )
        except Exception as e:
            print(f"[RAG Engine] Notice: Langfuse client initialization skipped: {e}")
            langfuse_client = None

    # LLM & Embeddings initialization
    llm = ChatOpenAI(
        model=model_name,
        temperature=0.3,
        api_key=api_key
    )

    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=api_key
    )

    # Compile LangGraph RAG Workflow
    rag_graph = build_rag_graph()
    print(f"[RAG Engine] Successfully initialized with LLM: {model_name}, Embeddings: text-embedding-3-small")


# --- State Definition for LangGraph ---

class SupportSessionState(TypedDict):
    session_id: str
    customer_name: str
    customer_email: str
    product: str
    query: str
    history: List[Dict[str, Any]]
    standalone_query: Optional[str]
    retrieved_tickets: Optional[List[Dict[str, Any]]]
    response: Optional[str]
    sources: Optional[List[Dict[str, Any]]]


# --- LangGraph Nodes ---

@observe(name="contextualize_query_node")
def contextualize_query_node(state: SupportSessionState) -> dict:
    """
    If there is prior conversation history, reformulate the latest query
    into a self-contained standalone search query.
    """
    history = state.get("history", [])
    query = state.get("query", "").strip()

    if not history:
        return {"standalone_query": query}

    # Build concise history string
    history_snippets = []
    for m in history[-6:]:  # Keep up to last 3 conversation turns
        sender = "Customer" if m.get("sender") == "user" else "Support"
        history_snippets.append(f"{sender}: {m.get('message', '')}")
    history_text = "\n".join(history_snippets)

    system_prompt = (
        "Given the following conversation between a Customer and Technical Support, "
        "and the customer's newest follow-up question, rephrase the newest question "
        "into a standalone search query that includes any necessary context (like the software product, "
        "operating system, or error keywords mentioned earlier). "
        "Do NOT answer the question, just return the reformulated query text."
    )

    try:
        rephrased = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Product: {state.get('product')}\nConversation History:\n{history_text}\n\nLatest Customer Message: {query}")
        ])
        standalone = rephrased.content.strip()
        if not standalone:
            standalone = query
    except Exception as e:
        print(f"[RAG Engine] Query contextualization fallback: {e}")
        standalone = query

    return {"standalone_query": standalone}


@observe(name="retrieve_tickets_node")
def retrieve_tickets_node(state: SupportSessionState) -> dict:
    """
    Retrieves the most relevant historical customer support tickets from SQLite
    filtered by product, using vector cosine similarity and keyword matching.
    """
    product = state.get("product", "")
    query_to_search = state.get("standalone_query") or state.get("query", "")

    # Fetch candidate tickets for this product
    tickets = database.get_all_tickets_for_product(product)
    if not tickets:
        # Fallback to all tickets if none found for specific product
        tickets = database.get_all_tickets_for_product(None)

    if not tickets:
        return {"retrieved_tickets": [], "sources": []}

    scored_tickets = []

    try:
        # Generate query vector embedding
        query_vec = embeddings_model.embed_query(query_to_search)
        q_norm = np.linalg.norm(query_vec)

        query_lower = query_to_search.lower()
        query_words = set(query_lower.split())

        for t in tickets:
            t_vec = t.get("embedding")
            sim_score = 0.0
            if t_vec:
                t_arr = np.array(t_vec)
                denom = q_norm * np.linalg.norm(t_arr)
                if denom > 0:
                    sim_score = float(np.dot(query_vec, t_arr) / denom)

            # Keyword lexical overlap boost
            ticket_text = (
                f"{t.get('ticket_code', '')} {t.get('category', '')} {t.get('customer_query', '')} "
                f"{t.get('resolution_summary', '')} {t.get('support_response', '')}"
            ).lower()

            keyword_hits = sum(1 for w in query_words if len(w) > 3 and w in ticket_text)
            combined_score = sim_score + (0.05 * keyword_hits)

            scored_tickets.append({
                "ticket_code": t.get("ticket_code"),
                "product": t.get("product"),
                "category": t.get("category"),
                "customer_query": t.get("customer_query"),
                "support_response": t.get("support_response"),
                "resolution_summary": t.get("resolution_summary"),
                "similarity_score": round(sim_score, 4),
                "combined_score": round(combined_score, 4)
            })

        # Sort by combined score descending
        scored_tickets.sort(key=lambda x: x["combined_score"], reverse=True)

        # Select top 3 relevant tickets
        top_tickets = scored_tickets[:3]

    except Exception as e:
        print(f"[RAG Engine] Vector retrieval error: {e}. Falling back to keyword search.")
        query_lower = query_to_search.lower()
        top_tickets = []
        for t in tickets:
            ticket_text = f"{t.get('customer_query', '')} {t.get('resolution_summary', '')}".lower()
            if any(w in ticket_text for w in query_lower.split() if len(w) > 3):
                top_tickets.append({
                    "ticket_code": t.get("ticket_code"),
                    "product": t.get("product"),
                    "category": t.get("category"),
                    "customer_query": t.get("customer_query"),
                    "support_response": t.get("support_response"),
                    "resolution_summary": t.get("resolution_summary"),
                    "similarity_score": 0.5,
                    "combined_score": 0.5
                })
        top_tickets = top_tickets[:3]

    # Format sources for UI display and citation
    sources = []
    for t in top_tickets:
        sources.append({
            "ticket_code": t["ticket_code"],
            "product": t["product"],
            "category": t["category"],
            "customer_query": t["customer_query"],
            "resolution_summary": t["resolution_summary"],
            "similarity_score": t.get("similarity_score", 0.0)
        })

    return {
        "retrieved_tickets": top_tickets,
        "sources": sources
    }


@observe(name="generate_response_node")
def generate_response_node(state: SupportSessionState) -> dict:
    """
    Generates grounded support response using retrieved historical tickets and session history.
    """
    customer_name = state.get("customer_name", "Customer")
    customer_email = state.get("customer_email", "")
    product = state.get("product", "our software")
    current_query = state.get("query", "")
    history = state.get("history", [])
    retrieved = state.get("retrieved_tickets", [])

    # Format historical ticket knowledge
    if retrieved:
        kb_sections = []
        for i, doc in enumerate(retrieved, start=1):
            kb_sections.append(
                f"### Historical Ticket {i}: [{doc['ticket_code']}] - Category: {doc['category']}\n"
                f"Customer Problem: {doc['customer_query']}\n"
                f"Resolution Summary: {doc['resolution_summary']}\n"
                f"Verified Support Team Response:\n{doc['support_response']}\n"
            )
        knowledge_context = "\n--------------------\n".join(kb_sections)
    else:
        knowledge_context = "No specific historical support tickets found matching this issue."

    # Build prompt messages
    system_instruction = (
        f"You are an expert, empathetic, and highly capable Technical Customer Support Engineer for '{product}'.\n"
        f"You are in a live support session assisting customer '{customer_name}' ({customer_email}).\n\n"
        "YOUR ROLE AND GUIDELINES:\n"
        "1. GROUNDING IN HISTORICAL SUPPORT DATA:\n"
        "   - You have access to our verified historical support ticket resolutions below.\n"
        "   - Use these historical resolutions as your primary source of truth.\n"
        "   - When citing specific troubleshooting steps, recommendations, or configurations from a ticket, "
        "reference the ticket code (e.g. '[Ref: CSP-101]').\n"
        "2. ACCURACY & PRACTICAL STEPS:\n"
        "   - Provide clear, step-by-step instructions with numbered lists, commands, or UI navigation paths.\n"
        "   - Format code blocks, commands, and file paths using markdown syntax (`...` or ```...```).\n"
        "3. TONE & EMPATHY:\n"
        "   - Be polite, courteous, empathetic, and professional.\n"
        "   - Acknowledge the user's issue and reassure them that you are here to help.\n"
        "4. CONVERSATIONAL CONTINUITY:\n"
        "   - Take the prior conversation history into account. Do not needlessly repeat what the customer already tried.\n"
        "5. OUT-OF-SCOPE / UNCLEAR ISSUES:\n"
        f"   - If the customer's query is completely unrelated to '{product}' or general IT issues, politely guide them back.\n\n"
        f"--- VERIFIED HISTORICAL SUPPORT KNOWLEDGE BASE ({product}) ---\n"
        f"{knowledge_context}\n"
        "--- END KNOWLEDGE BASE ---\n"
    )

    messages = [SystemMessage(content=system_instruction)]

    # Append conversation history
    for item in history:
        sender = item.get("sender")
        msg_text = item.get("message", "")
        if sender == "user":
            messages.append(HumanMessage(content=msg_text))
        elif sender == "assistant":
            messages.append(AIMessage(content=msg_text))

    # Append current user question
    messages.append(HumanMessage(content=current_query))

    try:
        ai_response = llm.invoke(messages)
        response_text = ai_response.content
    except Exception as e:
        print(f"[RAG Engine] LLM generation error: {e}")
        response_text = (
            f"I apologize, {customer_name}, but I encountered a temporary issue while generating the solution. "
            "Please try asking your question again in a moment."
        )

    return {"response": response_text}


# --- Build LangGraph Workflow ---

def build_rag_graph():
    """Builds and compiles the StateGraph workflow for Customer Support RAG."""
    workflow = StateGraph(SupportSessionState)

    # Add Nodes
    workflow.add_node("contextualize", contextualize_query_node)
    workflow.add_node("retrieve", retrieve_tickets_node)
    workflow.add_node("generate", generate_response_node)

    # Define Workflow Flow
    workflow.set_entry_point("contextualize")
    workflow.add_edge("contextualize", "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


# --- Main Public API ---

@observe(name="process_customer_support_query")
def process_support_query(session_id: str, customer_name: str, 
                          customer_email: str, product: str, 
                          query: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Main entry point for processing a customer's query within an active session.
    Traced via Langfuse @observe.
    """
    if rag_graph is None:
        init_rag_engine()
        

    initial_state: SupportSessionState = {
        "session_id": session_id,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "product": product,
        "query": query,
        "history": history or [],
        "standalone_query": None,
        "retrieved_tickets": None,
        "response": None,
        "sources": None
    }

    rag_graph.get_graph().draw_png(output_file_path="rag_engine.png")

    # Execute LangGraph state machine
    final_state = rag_graph.invoke(initial_state)

    # Flush Langfuse telemetry safely
    if langfuse_client:
        try:
            langfuse_client.flush()
        except Exception:
            pass

    return {
        "response": final_state.get("response", "No response generated."),
        "sources": final_state.get("sources", []),
        "standalone_query": final_state.get("standalone_query", query)
    }
